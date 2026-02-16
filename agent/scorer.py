"""
Trade Recommendation Scoring Engine (v2)
==========================================
Analyzes options data to generate scored trade recommendations.
Each ticker receives a score 0-100 based on 9 weighted signals.

Improvements over v1:
  1. Adaptive thresholds — percentile ranking vs ticker's own history
  2. Historical momentum — GEX trend + skew trend over recent hours
  3. IV Rank — compares current IV to historical range (replaces raw vega)
  4. DTE weighting — near-term contracts weighted heavier
  5. Backtesting log — every recommendation logged for outcome tracking

All data is sourced exclusively from Schwab API via the historical DB.

⚠️ DISCLAIMER: NOT financial advice. Scores reflect signal strength
for educational/informational purposes only.
"""

import json
import math
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
from datetime import datetime
from logger import get_logger
from agent.strategies import get_strategy

log = get_logger("agent.scorer")

# Signal weights (must sum to 100)
WEIGHTS = {
    'gex_regime':       20,
    'wall_proximity':   15,
    'pc_skew':          12,
    'volume_oi_surge':  12,
    'directional_bias': 10,
    'iv_rank':          10,
    'gex_momentum':      8,
    'skew_momentum':     5,
    'dte_conviction':    8,
}


@dataclass
class SignalScore:
    """Individual signal score with details."""
    name: str
    score: int         # 0 to weight_max
    max_score: int     # weight for this signal
    detail: str        # explanation


@dataclass
class Recommendation:
    """A scored trade recommendation for a ticker."""
    ticker: str
    score: int                    # 0-100
    direction: str                # "BULLISH", "BEARISH", "NEUTRAL"
    play_type: str                # "Call Spread", "Iron Condor", etc.
    reasoning: str                # Human-readable explanation
    risk_notes: str               # Key risks
    signals: List[dict] = field(default_factory=list)
    timestamp: str = ""
    price_at_score: float = 0.0
    iv_rank_value: float = 0.0
    net_gex_value: float = 0.0

    def to_dict(self):
        return asdict(self)


# ─── DTE Helper ───


def _compute_dte_weight(contracts: list, price: float) -> float:
    """Compute a DTE-based conviction multiplier from contract expirations.

    Near-term contracts get higher weight because they reflect
    active hedging that impacts price NOW.

    Returns:
        Multiplier 0.5–1.5 (>1 means heavy near-term positioning)
    """
    if not contracts or price <= 0:
        return 1.0

    lo, hi = price * 0.95, price * 1.05
    weighted_dte = 0
    total_oi = 0

    today = datetime.now().date()

    for c in contracts:
        strike = c.get('Strike', 0)
        if not (lo <= strike <= hi):
            continue
        oi = c.get('OpenInterest', 0) or 0
        if oi <= 0:
            continue

        exp_str = c.get('Expiration', '')
        if exp_str:
            try:
                exp_date = datetime.strptime(exp_str[:10], '%Y-%m-%d').date()
                dte = max((exp_date - today).days, 1)
            except (ValueError, TypeError):
                dte = 30  # fallback
        else:
            dte = 30

        weighted_dte += dte * oi
        total_oi += oi

    if total_oi == 0:
        return 1.0

    avg_dte = weighted_dte / total_oi

    # Curve: avg DTE=1 → 1.5x, avg DTE=7 → 1.2x, avg DTE=30 → 1.0x, avg DTE=90 → 0.7x
    if avg_dte <= 1:
        multiplier = 1.5
    elif avg_dte <= 7:
        multiplier = 1.5 - (avg_dte - 1) * 0.05  # 1.5 → 1.2
    elif avg_dte <= 30:
        multiplier = 1.2 - (avg_dte - 7) * 0.0087  # 1.2 → 1.0
    else:
        multiplier = max(0.5, 1.0 - (avg_dte - 30) * 0.005)  # 1.0 → 0.5

    return round(multiplier, 3)


# ─── Sub-Scorers ───


def _score_gex_regime(
    net_gex: float,
    percentile: float = 0.5,
    max_weight: int = 20,
) -> SignalScore:
    """Score based on net GEX using adaptive percentile thresholds.

    Uses the ticker's own GEX history for normalization instead of
    hardcoded thresholds. Higher percentile = stronger signal.
    """
    if net_gex is None or net_gex == 0:
        return SignalScore("GEX Regime", 0, max_weight, "No GEX data available")

    # Use percentile for scoring — extreme values (near 0 or 1) score highest
    distance_from_center = abs(percentile - 0.5) * 2  # 0..1
    raw = 0.2 + (distance_from_center * 0.8)  # floor at 0.2
    raw = min(1.0, raw)

    score = int(raw * max_weight)
    regime = "POSITIVE (mean-reversion)" if net_gex > 0 else "NEGATIVE (trending)"

    return SignalScore(
        "GEX Regime", score, max_weight,
        f"Net GEX: {net_gex:,.0f} → {regime} (percentile: {percentile:.0%})"
    )


def _score_wall_proximity(
    price: float,
    pos_strike: Optional[float],
    neg_strike: Optional[float],
    max_weight: int = 15,
) -> SignalScore:
    """Score based on how close price is to a gamma wall.

    Closer to a wall = higher conviction play (bounce or rejection).
    """
    if price <= 0:
        return SignalScore("Wall Proximity", 0, max_weight, "No price data")

    best_dist_pct = 100.0
    wall_name = "none"

    if pos_strike and pos_strike > 0:
        dist = abs(price - pos_strike) / price * 100
        if dist < best_dist_pct:
            best_dist_pct = dist
            wall_name = f"call wall ${pos_strike:,.0f}"

    if neg_strike and neg_strike > 0:
        dist = abs(price - neg_strike) / price * 100
        if dist < best_dist_pct:
            best_dist_pct = dist
            wall_name = f"put wall ${neg_strike:,.0f}"

    if best_dist_pct <= 0.5:
        raw = 1.0
    elif best_dist_pct <= 1.0:
        raw = 0.85
    elif best_dist_pct <= 2.0:
        raw = 0.65
    elif best_dist_pct <= 5.0:
        raw = 0.4
    else:
        raw = 0.15

    score = int(raw * max_weight)
    return SignalScore(
        "Wall Proximity", score, max_weight,
        f"Price ${price:,.2f} is {best_dist_pct:.1f}% from {wall_name}"
    )


def _score_pc_skew(
    contracts: list,
    price: float,
    dte_multiplier: float = 1.0,
    max_weight: int = 12,
) -> SignalScore:
    """Score based on put/call OI ratio near ATM strikes.

    Uses DTE-weighted OI: near-term contracts count more.
    """
    if not contracts or price <= 0:
        return SignalScore("P/C Skew", 0, max_weight, "No contract data")

    lo, hi = price * 0.95, price * 1.05
    call_oi, put_oi = 0, 0
    today = datetime.now().date()

    for c in contracts:
        strike = c.get('Strike', 0)
        if not (lo <= strike <= hi):
            continue
        oi = c.get('OpenInterest', 0) or 0

        # DTE weighting: shorter expiration = more weight
        exp_str = c.get('Expiration', '')
        dte_w = 1.0
        if exp_str:
            try:
                exp_date = datetime.strptime(exp_str[:10], '%Y-%m-%d').date()
                dte = max((exp_date - today).days, 1)
                dte_w = 1.0 / math.sqrt(dte)  # sqrt decay for smoother weighting
            except (ValueError, TypeError):
                pass

        weighted_oi = oi * dte_w
        if c.get('Type') == 'CALL':
            call_oi += weighted_oi
        elif c.get('Type') == 'PUT':
            put_oi += weighted_oi

    if call_oi == 0 and put_oi == 0:
        return SignalScore("P/C Skew", 0, max_weight, "No ATM OI data")

    pc_ratio = put_oi / call_oi if call_oi > 0 else 999

    if pc_ratio > 2.0 or pc_ratio < 0.5:
        raw = 1.0
    elif pc_ratio > 1.5 or pc_ratio < 0.67:
        raw = 0.75
    elif pc_ratio > 1.2 or pc_ratio < 0.83:
        raw = 0.5
    else:
        raw = 0.25

    skew_dir = "PUT-heavy (bearish)" if pc_ratio > 1.2 else "CALL-heavy (bullish)" if pc_ratio < 0.83 else "balanced"
    score = int(raw * max_weight)

    return SignalScore(
        "P/C Skew", score, max_weight,
        f"P/C ratio {pc_ratio:.2f} ({skew_dir}) — DTE-weighted"
    )


def _score_volume_oi_surge(
    contracts: list,
    price: float,
    dte_multiplier: float = 1.0,
    max_weight: int = 12,
) -> SignalScore:
    """Score based on unusual volume relative to OI near ATM strikes.

    DTE-weighted: near-term surges score higher.
    """
    if not contracts or price <= 0:
        return SignalScore("Vol/OI Surge", 0, max_weight, "No contract data")

    lo, hi = price * 0.95, price * 1.05
    total_vol, total_oi = 0, 0
    surge_strikes = []
    today = datetime.now().date()

    for c in contracts:
        strike = c.get('Strike', 0)
        if not (lo <= strike <= hi):
            continue
        vol = c.get('Volume', 0) or 0
        oi = c.get('OpenInterest', 0) or 0

        exp_str = c.get('Expiration', '')
        dte_w = 1.0
        if exp_str:
            try:
                exp_date = datetime.strptime(exp_str[:10], '%Y-%m-%d').date()
                dte = max((exp_date - today).days, 1)
                dte_w = 1.0 / math.sqrt(dte)
            except (ValueError, TypeError):
                pass

        total_vol += vol * dte_w
        total_oi += oi * dte_w

        if oi > 0 and vol / oi > 0.5:
            surge_strikes.append(strike)

    vol_oi_ratio = total_vol / total_oi if total_oi > 0 else 0

    if vol_oi_ratio > 1.0:
        raw = 1.0
    elif vol_oi_ratio > 0.5:
        raw = 0.75
    elif vol_oi_ratio > 0.25:
        raw = 0.5
    elif vol_oi_ratio > 0.1:
        raw = 0.3
    else:
        raw = 0.1

    score = int(raw * max_weight)
    surge_note = f" ({len(surge_strikes)} surge strikes)" if surge_strikes else ""

    return SignalScore(
        "Vol/OI Surge", score, max_weight,
        f"Vol/OI ratio: {vol_oi_ratio:.2f}{surge_note} — DTE-weighted"
    )


def _score_iv_rank(
    iv_rank: float,
    max_weight: int = 10,
) -> SignalScore:
    """Score based on IV rank (percentile of current IV vs historical range).

    Extreme IV ranks (very high or very low) = stronger signal.
    High IV = sell premium. Low IV = buy premium.
    """
    if iv_rank is None:
        return SignalScore("IV Rank", 0, max_weight, "No IV data available")

    # Extreme values score higher
    distance_from_center = abs(iv_rank - 0.5) * 2  # 0..1
    raw = 0.1 + (distance_from_center * 0.9)

    score = int(raw * max_weight)

    if iv_rank >= 0.8:
        outlook = f"HIGH ({iv_rank:.0%}) — sell premium, vol crush expected"
    elif iv_rank >= 0.5:
        outlook = f"ELEVATED ({iv_rank:.0%}) — neutral to sell"
    elif iv_rank >= 0.2:
        outlook = f"LOW ({iv_rank:.0%}) — buy premium opportunity"
    else:
        outlook = f"VERY LOW ({iv_rank:.0%}) — strong vol expansion expected"

    return SignalScore("IV Rank", score, max_weight, f"IV Rank: {outlook}")


def _score_directional_bias(
    analytics: dict,
    price: float,
    max_weight: int = 10,
) -> SignalScore:
    """Score based on net dealer delta exposure."""
    if not analytics or not analytics.get('strikes') or price <= 0:
        return SignalScore("Directional Bias", 0, max_weight, "No analytics data")

    strikes = analytics['strikes']
    lo, hi = price * 0.9, price * 1.1
    net_delta = 0

    for strike_key, data in strikes.items():
        s = float(strike_key)
        if lo <= s <= hi:
            net_delta += data.get('total_delta', 0)

    abs_delta = abs(net_delta)

    if abs_delta > 500_000:
        raw = 1.0
    elif abs_delta > 100_000:
        raw = 0.75
    elif abs_delta > 25_000:
        raw = 0.5
    elif abs_delta > 5_000:
        raw = 0.3
    else:
        raw = 0.1

    direction = "BULLISH" if net_delta > 0 else "BEARISH" if net_delta < 0 else "FLAT"
    score = int(raw * max_weight)

    return SignalScore(
        "Directional Bias", score, max_weight,
        f"Net delta: {net_delta:,.0f} → {direction} dealer positioning"
    )


def _score_gex_momentum(
    momentum: dict,
    max_weight: int = 8,
) -> SignalScore:
    """Score based on GEX trend over recent hours.

    Rising GEX = strengthening mean-reversion (bullish stability).
    Falling GEX = weakening support (bearish risk).
    """
    if not momentum or momentum.get('gex_samples', 0) < 2:
        return SignalScore("GEX Momentum", 0, max_weight, "Insufficient history")

    trend = momentum.get('gex_trend', 0)
    abs_trend = abs(trend)

    if abs_trend > 0.5:
        raw = 1.0     # strong trend
    elif abs_trend > 0.25:
        raw = 0.7     # moderate trend
    elif abs_trend > 0.1:
        raw = 0.4     # weak trend
    else:
        raw = 0.15    # flat

    score = int(raw * max_weight)
    direction = "RISING" if trend > 0.05 else "FALLING" if trend < -0.05 else "FLAT"

    return SignalScore(
        "GEX Momentum", score, max_weight,
        f"GEX trend: {direction} ({trend:+.1%}) over {momentum.get('gex_samples', 0)} samples"
    )


def _score_skew_momentum(
    contracts: list,
    price: float,
    previous_pc_ratio: Optional[float] = None,
    max_weight: int = 5,
) -> SignalScore:
    """Score based on P/C ratio direction of change.

    Rapidly shifting skew = new institutional positioning.
    """
    if not contracts or price <= 0:
        return SignalScore("Skew Momentum", 0, max_weight, "No contract data")

    # Compute current P/C ratio
    lo, hi = price * 0.95, price * 1.05
    call_oi, put_oi = 0, 0

    for c in contracts:
        strike = c.get('Strike', 0)
        if not (lo <= strike <= hi):
            continue
        oi = c.get('OpenInterest', 0) or 0
        if c.get('Type') == 'CALL':
            call_oi += oi
        elif c.get('Type') == 'PUT':
            put_oi += oi

    if call_oi == 0 and put_oi == 0:
        return SignalScore("Skew Momentum", 0, max_weight, "No ATM OI")

    current_ratio = put_oi / call_oi if call_oi > 0 else 999

    if previous_pc_ratio is None or previous_pc_ratio <= 0:
        return SignalScore(
            "Skew Momentum", int(0.2 * max_weight), max_weight,
            f"Current P/C: {current_ratio:.2f} (no history for trend)"
        )

    # How much did the ratio change?
    change = (current_ratio - previous_pc_ratio) / previous_pc_ratio
    abs_change = abs(change)

    if abs_change > 0.3:
        raw = 1.0    # massive shift
    elif abs_change > 0.15:
        raw = 0.7
    elif abs_change > 0.05:
        raw = 0.4
    else:
        raw = 0.15

    score = int(raw * max_weight)
    direction = "PUTS increasing" if change > 0.05 else "CALLS increasing" if change < -0.05 else "Stable"

    return SignalScore(
        "Skew Momentum", score, max_weight,
        f"P/C shift: {change:+.1%} → {direction}"
    )


def _score_dte_conviction(
    dte_multiplier: float,
    max_weight: int = 8,
) -> SignalScore:
    """Score based on DTE weighting — heavy near-term OI = high conviction."""
    if dte_multiplier >= 1.4:
        raw = 1.0
        detail = "Very heavy 0-2 DTE positioning — imminent move expected"
    elif dte_multiplier >= 1.2:
        raw = 0.75
        detail = "Elevated near-term activity — 1-7 DTE dominant"
    elif dte_multiplier >= 1.0:
        raw = 0.45
        detail = "Standard DTE distribution — no near-term urgency"
    elif dte_multiplier >= 0.7:
        raw = 0.25
        detail = "Longer-dated positioning — structural, not immediate"
    else:
        raw = 0.1
        detail = "Far-dated positioning — watch but low conviction"

    score = int(raw * max_weight)
    return SignalScore(
        "DTE Conviction", score, max_weight,
        f"DTE multiplier: {dte_multiplier:.2f} — {detail}"
    )


# ─── Main Scorer ───


def score_ticker(
    ticker: str,
    contracts: list,
    analytics: dict,
    gamma_levels: dict,
    historical_context: dict = None,
) -> Recommendation:
    """Score a single ticker and produce a trade recommendation.

    Args:
        ticker: Symbol (e.g. "SPY")
        contracts: Raw option contracts for this ticker
        analytics: Aggregated strike-level data { price, strikes: { ... } }
        gamma_levels: { max_positive_gamma_strike, max_negative_gamma_strike, ... }
        historical_context: Optional DB-sourced historical data:
            { gex_percentile, momentum, iv_rank, previous_pc_ratio }
    """
    if historical_context is None:
        historical_context = {}

    price = analytics.get('price', 0) if analytics else 0
    pos_strike = gamma_levels.get('max_positive_gamma_strike') if gamma_levels else None
    neg_strike = gamma_levels.get('max_negative_gamma_strike') if gamma_levels else None

    pos_gex = gamma_levels.get('max_positive_gamma_value', 0) or 0 if gamma_levels else 0
    neg_gex = gamma_levels.get('max_negative_gamma_value', 0) or 0 if gamma_levels else 0
    net_gex = pos_gex + neg_gex

    # Historical data
    gex_percentile = historical_context.get('gex_percentile', 0.5)
    momentum = historical_context.get('momentum', {})
    iv_rank = historical_context.get('iv_rank', 0.5)
    prev_pc = historical_context.get('previous_pc_ratio')

    # DTE analysis
    dte_mult = _compute_dte_weight(contracts, price)

    # Score all 9 signals
    s1 = _score_gex_regime(net_gex, gex_percentile, WEIGHTS['gex_regime'])
    s2 = _score_wall_proximity(price, pos_strike, neg_strike, WEIGHTS['wall_proximity'])
    s3 = _score_pc_skew(contracts, price, dte_mult, WEIGHTS['pc_skew'])
    s4 = _score_volume_oi_surge(contracts, price, dte_mult, WEIGHTS['volume_oi_surge'])
    s5 = _score_iv_rank(iv_rank, WEIGHTS['iv_rank'])
    s6 = _score_directional_bias(analytics, price, WEIGHTS['directional_bias'])
    s7 = _score_gex_momentum(momentum, WEIGHTS['gex_momentum'])
    s8 = _score_skew_momentum(contracts, price, prev_pc, WEIGHTS['skew_momentum'])
    s9 = _score_dte_conviction(dte_mult, WEIGHTS['dte_conviction'])

    all_signals = [s1, s2, s3, s4, s5, s6, s7, s8, s9]
    total_score = sum(s.score for s in all_signals)
    total_score = max(0, min(100, total_score))

    # Strategy lookup inputs
    gex_regime = "positive" if net_gex >= 0 else "negative"

    if price > 0 and pos_strike and abs(price - pos_strike) / price * 100 <= 3:
        wall_position = "near_call_wall"
    elif price > 0 and neg_strike and abs(price - neg_strike) / price * 100 <= 3:
        wall_position = "near_put_wall"
    else:
        wall_position = "mid_range"

    pc_detail = s3.detail
    delta_detail = s6.detail
    if "PUT-heavy" in pc_detail or "BEARISH" in delta_detail:
        skew = "bearish"
    elif "CALL-heavy" in pc_detail or "BULLISH" in delta_detail:
        skew = "bullish"
    else:
        skew = "neutral"

    strategy = get_strategy(gex_regime, wall_position, skew)

    # Build reasoning
    top_signals = sorted(all_signals, key=lambda s: s.score, reverse=True)
    reasoning_parts = [f"[{s.name}: {s.score}/{s.max_score}] {s.detail}" for s in top_signals[:3]]
    reasoning = f"{strategy.description}. Top signals: " + " | ".join(reasoning_parts)

    # Risk notes
    risk_parts = []
    if gex_regime == "negative":
        risk_parts.append("Negative GEX = volatile regime, wider stops needed")
    if wall_position == "mid_range":
        risk_parts.append("No nearby gamma wall support/resistance")
    if "balanced" in pc_detail.lower():
        risk_parts.append("No clear directional conviction from OI skew")
    if total_score < 40:
        risk_parts.append("Low overall signal strength — consider smaller position")
    if iv_rank > 0.8:
        risk_parts.append("IV elevated — premium expensive, define risk carefully")
    risk_notes = "; ".join(risk_parts) if risk_parts else "Standard risk management applies"

    return Recommendation(
        ticker=ticker,
        score=total_score,
        direction=strategy.direction,
        play_type=strategy.play_type,
        reasoning=reasoning,
        risk_notes=risk_notes,
        signals=[asdict(s) for s in all_signals],
        timestamp=datetime.now().isoformat(),
        price_at_score=price,
        iv_rank_value=iv_rank,
        net_gex_value=net_gex,
    )


def _fetch_historical_context(ticker: str) -> dict:
    """Pre-fetch all historical data needed for scoring a ticker.

    Pulls exclusively from the Schwab-sourced historical DB.
    """
    context = {
        'gex_percentile': 0.5,
        'momentum': {},
        'iv_rank': 0.5,
        'previous_pc_ratio': None,
    }

    try:
        from db.queries import get_historical_percentile, get_signal_momentum, get_iv_percentile
        from db.queries import get_gamma_history

        # Get current net GEX for percentile ranking
        history = get_gamma_history(ticker, hours=1)
        if history:
            current_gex = history[-1].get('net_gex', 0) or 0
            context['gex_percentile'] = get_historical_percentile(
                ticker, 'net_gex', abs(current_gex), hours=168
            )

        # Momentum over last 4 hours
        context['momentum'] = get_signal_momentum(ticker, hours=4)

        # IV rank from historical data
        context['iv_rank'] = get_iv_percentile(ticker, hours=168)

    except Exception as e:
        log.debug("Historical context for %s unavailable: %s", ticker, e)

    return context


def score_all_tickers(
    all_contracts: list,
    analytics_data: dict,
    gamma_data: dict,
) -> List[Recommendation]:
    """Score all tickers and return sorted recommendations.

    Pre-fetches historical context from the DB (Schwab data only)
    once per cycle to feed adaptive scoring.
    """
    by_ticker = {}
    for c in all_contracts:
        t = c.get('Symbol', '')
        if t:
            by_ticker.setdefault(t, []).append(c)

    all_tickers = set(by_ticker.keys())
    if analytics_data:
        all_tickers |= set(analytics_data.keys())
    if gamma_data:
        all_tickers |= set(gamma_data.keys())

    recommendations = []
    for ticker in sorted(all_tickers):
        try:
            contracts = by_ticker.get(ticker, [])
            analytics = analytics_data.get(ticker, {}) if analytics_data else {}
            gamma = gamma_data.get(ticker, {}) if gamma_data else {}

            # Fetch historical context from Schwab-sourced DB
            hist_ctx = _fetch_historical_context(ticker)

            rec = score_ticker(ticker, contracts, analytics, gamma, hist_ctx)
            recommendations.append(rec)
        except Exception as e:
            log.warning("Failed to score %s: %s", ticker, e)

    recommendations.sort(key=lambda r: r.score, reverse=True)

    log.info("Scored %d tickers. Top 5: %s",
             len(recommendations),
             ", ".join(f"{r.ticker}({r.score})" for r in recommendations[:5]))

    return recommendations


def save_recommendations(recommendations: List[Recommendation], filepath: str = "recommendations.json"):
    """Save recommendations to JSON file AND log to DB for backtesting."""
    data = {
        "generated_at": datetime.now().isoformat(),
        "total_tickers": len(recommendations),
        "disclaimer": "NOT financial advice. Scores reflect signal strength for educational purposes only.",
        "recommendations": [r.to_dict() for r in recommendations],
    }

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    # Log to database for backtesting
    try:
        from db.storage import save_recommendation_log
        log_entries = [{
            'ticker': r.ticker,
            'score': r.score,
            'direction': r.direction,
            'play_type': r.play_type,
            'price_at_score': r.price_at_score,
            'net_gex': r.net_gex_value,
            'iv_rank': r.iv_rank_value,
        } for r in recommendations]
        save_recommendation_log(log_entries)
    except Exception as e:
        log.warning("Could not log recommendations for backtesting: %s", e)

    log.info("Saved %d recommendations to %s", len(recommendations), filepath)
    return data

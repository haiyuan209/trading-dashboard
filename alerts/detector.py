"""
Alert Detection Logic
======================
Detects significant changes in gamma exposure, key level breaches,
and unusual activity to generate actionable alerts.
"""

from dataclasses import dataclass
from typing import List, Optional
from logger import get_logger

log = get_logger("alerts.detector")


@dataclass
class Alert:
    """Represents a trading alert."""
    ticker: str
    alert_type: str       # "gex_flip", "new_max_strike", "price_near_wall"
    severity: str         # "info", "warning", "critical"
    message: str
    details: Optional[str] = None


def detect_gex_flip(ticker: str, current_net_gex: float, previous_net_gex: float) -> Optional[Alert]:
    """Detect when net GEX flips from positive to negative or vice versa.

    A positive-to-negative flip means dealers shift from stabilizing to amplifying moves.
    """
    if previous_net_gex is None or current_net_gex is None:
        return None

    if previous_net_gex > 0 and current_net_gex < 0:
        return Alert(
            ticker=ticker,
            alert_type="gex_flip",
            severity="critical",
            message=f"⚠️ {ticker}: GEX flipped NEGATIVE — dealers now amplify moves",
            details=f"Net GEX went from +{previous_net_gex:,.0f} to {current_net_gex:,.0f}. "
                    f"Expect increased volatility and trend acceleration."
        )
    elif previous_net_gex < 0 and current_net_gex > 0:
        return Alert(
            ticker=ticker,
            alert_type="gex_flip",
            severity="warning",
            message=f"✅ {ticker}: GEX flipped POSITIVE — dealers now stabilize",
            details=f"Net GEX went from {previous_net_gex:,.0f} to +{current_net_gex:,.0f}. "
                    f"Expect mean-reverting, range-bound behavior."
        )
    return None


def detect_new_max_strike(
    ticker: str,
    current_pos_strike: float,
    current_neg_strike: float,
    previous_pos_strike: float,
    previous_neg_strike: float,
) -> List[Alert]:
    """Detect when the max positive or negative gamma strike has shifted."""
    alerts = []

    if (current_pos_strike is not None and previous_pos_strike is not None
            and current_pos_strike != previous_pos_strike):
        alerts.append(Alert(
            ticker=ticker,
            alert_type="new_max_strike",
            severity="info",
            message=f"📊 {ticker}: Call wall shifted ${previous_pos_strike:.1f} → ${current_pos_strike:.1f}",
            details=f"Max positive GEX strike (resistance) moved from "
                    f"${previous_pos_strike:.1f} to ${current_pos_strike:.1f}"
        ))

    if (current_neg_strike is not None and previous_neg_strike is not None
            and current_neg_strike != previous_neg_strike):
        alerts.append(Alert(
            ticker=ticker,
            alert_type="new_max_strike",
            severity="info",
            message=f"📊 {ticker}: Put wall shifted ${previous_neg_strike:.1f} → ${current_neg_strike:.1f}",
            details=f"Max negative GEX strike (support) moved from "
                    f"${previous_neg_strike:.1f} to ${current_neg_strike:.1f}"
        ))

    return alerts


def detect_price_near_wall(
    ticker: str,
    price: float,
    pos_strike: float,
    neg_strike: float,
    threshold_pct: float = 1.0,
) -> List[Alert]:
    """Detect when current price is within threshold_pct of a gamma wall."""
    alerts = []

    if price <= 0:
        return alerts

    if pos_strike is not None and pos_strike > 0:
        distance_pct = abs(price - pos_strike) / price * 100
        if distance_pct <= threshold_pct:
            alerts.append(Alert(
                ticker=ticker,
                alert_type="price_near_wall",
                severity="warning",
                message=f"🎯 {ticker}: Price ${price:.2f} within {distance_pct:.1f}% of call wall ${pos_strike:.1f}",
                details=f"Approaching max positive GEX strike (resistance). "
                        f"Expect selling pressure from dealer hedging."
            ))

    if neg_strike is not None and neg_strike > 0:
        distance_pct = abs(price - neg_strike) / price * 100
        if distance_pct <= threshold_pct:
            alerts.append(Alert(
                ticker=ticker,
                alert_type="price_near_wall",
                severity="warning",
                message=f"🎯 {ticker}: Price ${price:.2f} within {distance_pct:.1f}% of put wall ${neg_strike:.1f}",
                details=f"Approaching max negative GEX strike (support). "
                        f"Expect buying pressure from dealer hedging."
            ))

    return alerts


def run_all_checks(
    current_data: dict,
    previous_data: dict,
    threshold_pct: float = 1.0,
    check_gex_flip: bool = True,
    check_max_strike: bool = True,
    check_price_wall: bool = True,
) -> List[Alert]:
    """Run all alert checks comparing current vs previous gamma data.

    Args:
        current_data: { ticker: { price, max_positive_gamma_strike, max_negative_gamma_strike, ... } }
        previous_data: Same structure from previous fetch cycle
        threshold_pct: % distance threshold for price-near-wall alerts
        check_*: Flags to enable/disable specific alert types

    Returns:
        List of Alert objects
    """
    all_alerts = []

    for ticker, current in current_data.items():
        previous = previous_data.get(ticker, {}) if previous_data else {}

        price = current.get('price', 0)
        cur_pos = current.get('max_positive_gamma_strike')
        cur_neg = current.get('max_negative_gamma_strike')
        cur_pos_gex = current.get('max_positive_gamma_value', 0)
        cur_neg_gex = current.get('max_negative_gamma_value', 0)
        cur_net_gex = (cur_pos_gex or 0) + (cur_neg_gex or 0)

        prev_pos = previous.get('max_positive_gamma_strike')
        prev_neg = previous.get('max_negative_gamma_strike')
        prev_pos_gex = previous.get('max_positive_gamma_value', 0)
        prev_neg_gex = previous.get('max_negative_gamma_value', 0)
        prev_net_gex = (prev_pos_gex or 0) + (prev_neg_gex or 0) if previous else None

        # Check GEX flip
        if check_gex_flip:
            alert = detect_gex_flip(ticker, cur_net_gex, prev_net_gex)
            if alert:
                all_alerts.append(alert)

        # Check max strike shifts
        if check_max_strike:
            alerts = detect_new_max_strike(ticker, cur_pos, cur_neg, prev_pos, prev_neg)
            all_alerts.extend(alerts)

        # Check price near gamma wall
        if check_price_wall:
            alerts = detect_price_near_wall(ticker, price, cur_pos, cur_neg, threshold_pct)
            all_alerts.extend(alerts)

    # Sort: critical first, then warning, then info
    severity_order = {'critical': 0, 'warning': 1, 'info': 2}
    all_alerts.sort(key=lambda a: severity_order.get(a.severity, 99))

    if all_alerts:
        log.info("Detected %d alerts across %d tickers", len(all_alerts), len(current_data))

    return all_alerts

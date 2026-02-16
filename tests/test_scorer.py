"""
Tests for Trade Recommendation Scorer v2
==========================================
Verifies all 9 signal scorers, DTE weighting, score bounds, and edge cases.
Uses deterministic test inputs — production scorer uses only Schwab API data.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.scorer import (
    _score_gex_regime,
    _score_wall_proximity,
    _score_pc_skew,
    _score_volume_oi_surge,
    _score_iv_rank,
    _score_directional_bias,
    _score_gex_momentum,
    _score_skew_momentum,
    _score_dte_conviction,
    _compute_dte_weight,
    score_ticker,
    score_all_tickers,
    Recommendation,
    WEIGHTS,
)


def make_contracts(ticker='SPY', price=590, call_oi=10000, put_oi=8000,
                   gamma=0.02, delta=0.5, volume=1500, expiration='2026-02-21'):
    """Generate a set of test contracts near ATM."""
    contracts = []
    for strike_offset in range(-5, 6):
        strike = price + strike_offset
        contracts.append({
            'Symbol': ticker, 'Strike': strike, 'Type': 'CALL',
            'OpenInterest': call_oi, 'Gamma': gamma, 'Delta': delta,
            'Vega': 0.15, 'Theta': -0.05, 'Volume': volume,
            'UnderlyingPrice': price, 'Expiration': expiration,
        })
        contracts.append({
            'Symbol': ticker, 'Strike': strike, 'Type': 'PUT',
            'OpenInterest': put_oi, 'Gamma': gamma, 'Delta': -delta,
            'Vega': 0.15, 'Theta': -0.05, 'Volume': volume,
            'UnderlyingPrice': price, 'Expiration': expiration,
        })
    return contracts


def make_analytics(price=590):
    """Generate test analytics data."""
    strikes = {}
    for offset in range(-5, 6):
        s = price + offset
        strikes[s] = {
            'total_gamma': 0.02 * 10000,
            'total_delta': 0.5 * 10000,
            'total_vega': 0.15 * 10000,
            'total_theta': -0.05 * 10000,
            'oi': 18000, 'volume': 3000,
        }
    return {'price': price, 'strikes': strikes}


def make_gamma_levels(pos_strike=595, neg_strike=580, pos_gex=1000000, neg_gex=-500000):
    return {
        'max_positive_gamma_strike': pos_strike,
        'max_negative_gamma_strike': neg_strike,
        'max_positive_gamma_value': pos_gex,
        'max_negative_gamma_value': neg_gex,
    }


# ─── Weight Tests ───

class TestWeights:
    def test_weights_sum_to_100(self):
        assert sum(WEIGHTS.values()) == 100

    def test_all_weights_positive(self):
        for name, w in WEIGHTS.items():
            assert w > 0, f"Weight {name} must be positive"

    def test_nine_signals(self):
        assert len(WEIGHTS) == 9


# ─── GEX Regime (adaptive percentile) ───

class TestGexRegimeScorer:
    def test_positive_gex(self):
        s = _score_gex_regime(5_000_000, percentile=0.9)
        assert 0 < s.score <= 20
        assert "POSITIVE" in s.detail

    def test_negative_gex(self):
        s = _score_gex_regime(-5_000_000, percentile=0.9)
        assert 0 < s.score <= 20
        assert "NEGATIVE" in s.detail

    def test_zero_gex(self):
        s = _score_gex_regime(0)
        assert s.score == 0

    def test_none_gex(self):
        s = _score_gex_regime(None)
        assert s.score == 0

    def test_extreme_percentile_scores_higher(self):
        low = _score_gex_regime(1_000_000, percentile=0.5)
        high = _score_gex_regime(1_000_000, percentile=0.95)
        assert high.score >= low.score

    def test_percentile_in_detail(self):
        s = _score_gex_regime(1_000_000, percentile=0.75)
        assert "75%" in s.detail


# ─── Wall Proximity ───

class TestWallProximityScorer:
    def test_at_call_wall(self):
        s = _score_wall_proximity(590, 590, 570)
        assert s.score >= 12

    def test_far_from_walls(self):
        s = _score_wall_proximity(590, 650, 530)
        assert s.score <= 5

    def test_no_price(self):
        s = _score_wall_proximity(0, 590, 580)
        assert s.score == 0

    def test_no_walls(self):
        s = _score_wall_proximity(590, None, None)
        assert s.score <= 5


# ─── P/C Skew (DTE-weighted) ───

class TestPcSkewScorer:
    def test_put_heavy(self):
        contracts = make_contracts(put_oi=25000, call_oi=5000)
        s = _score_pc_skew(contracts, 590)
        assert s.score > 0
        assert "PUT-heavy" in s.detail

    def test_call_heavy(self):
        contracts = make_contracts(put_oi=3000, call_oi=20000)
        s = _score_pc_skew(contracts, 590)
        assert "CALL-heavy" in s.detail

    def test_balanced(self):
        contracts = make_contracts(put_oi=10000, call_oi=10000)
        s = _score_pc_skew(contracts, 590)
        assert "balanced" in s.detail

    def test_no_contracts(self):
        s = _score_pc_skew([], 590)
        assert s.score == 0

    def test_dte_weighted_label(self):
        contracts = make_contracts()
        s = _score_pc_skew(contracts, 590)
        assert "DTE-weighted" in s.detail


# ─── Volume/OI Surge (DTE-weighted) ───

class TestVolOiSurgeScorer:
    def test_high_volume(self):
        contracts = make_contracts(volume=20000, call_oi=10000)
        s = _score_volume_oi_surge(contracts, 590)
        assert s.score > 5

    def test_low_volume(self):
        contracts = make_contracts(volume=100, call_oi=50000)
        s = _score_volume_oi_surge(contracts, 590)
        assert s.score <= 4


# ─── IV Rank (replaces raw vega) ───

class TestIvRankScorer:
    def test_high_iv(self):
        s = _score_iv_rank(0.9)
        assert s.score > 5
        assert "HIGH" in s.detail

    def test_low_iv(self):
        s = _score_iv_rank(0.15)
        assert s.score > 3
        assert "LOW" in s.detail

    def test_mid_iv(self):
        s = _score_iv_rank(0.5)
        assert s.score <= 3  # less extreme = lower score

    def test_none_iv(self):
        s = _score_iv_rank(None)
        assert s.score == 0


# ─── Directional Bias ───

class TestDirectionalBiasScorer:
    def test_bullish_delta(self):
        analytics = make_analytics()
        s = _score_directional_bias(analytics, 590)
        assert s.score > 0
        assert "BULLISH" in s.detail

    def test_no_analytics(self):
        s = _score_directional_bias({}, 590)
        assert s.score == 0


# ─── GEX Momentum (NEW) ───

class TestGexMomentumScorer:
    def test_strong_uptrend(self):
        momentum = {'gex_trend': 0.8, 'gex_samples': 10, 'gex_start': 100, 'gex_end': 180}
        s = _score_gex_momentum(momentum)
        assert s.score >= 6
        assert "RISING" in s.detail

    def test_strong_downtrend(self):
        momentum = {'gex_trend': -0.7, 'gex_samples': 10, 'gex_start': 200, 'gex_end': 60}
        s = _score_gex_momentum(momentum)
        assert s.score >= 5
        assert "FALLING" in s.detail

    def test_flat_trend(self):
        momentum = {'gex_trend': 0.02, 'gex_samples': 10, 'gex_start': 100, 'gex_end': 102}
        s = _score_gex_momentum(momentum)
        assert s.score <= 2
        assert "FLAT" in s.detail

    def test_insufficient_samples(self):
        momentum = {'gex_trend': 0.5, 'gex_samples': 1}
        s = _score_gex_momentum(momentum)
        assert s.score == 0


# ─── Skew Momentum (NEW) ───

class TestSkewMomentumScorer:
    def test_with_previous(self):
        contracts = make_contracts(put_oi=15000, call_oi=10000)
        s = _score_skew_momentum(contracts, 590, previous_pc_ratio=1.0)
        assert s.score > 0

    def test_without_previous(self):
        contracts = make_contracts()
        s = _score_skew_momentum(contracts, 590, previous_pc_ratio=None)
        assert s.score >= 0


# ─── DTE Conviction (NEW) ───

class TestDteConviction:
    def test_high_multiplier(self):
        s = _score_dte_conviction(1.45)
        assert s.score >= 6
        assert "0-2 DTE" in s.detail

    def test_low_multiplier(self):
        s = _score_dte_conviction(0.6)
        assert s.score <= 2

    def test_standard_multiplier(self):
        s = _score_dte_conviction(1.0)
        assert 2 <= s.score <= 5


# ─── DTE Weight Computation ───

class TestDteWeight:
    def test_near_term_high(self):
        contracts = make_contracts(expiration='2026-02-16')  # ~1 day
        w = _compute_dte_weight(contracts, 590)
        assert w >= 1.2

    def test_far_term_low(self):
        contracts = make_contracts(expiration='2026-05-15')  # ~90 days
        w = _compute_dte_weight(contracts, 590)
        assert w <= 1.0

    def test_empty_contracts(self):
        w = _compute_dte_weight([], 590)
        assert w == 1.0


# ─── Integration Tests ───

class TestScoreTicker:
    def test_returns_recommendation(self):
        contracts = make_contracts()
        analytics = make_analytics()
        gamma = make_gamma_levels()
        rec = score_ticker('SPY', contracts, analytics, gamma)
        assert isinstance(rec, Recommendation)
        assert rec.ticker == 'SPY'
        assert 0 <= rec.score <= 100
        assert rec.direction in ('BULLISH', 'BEARISH', 'NEUTRAL')
        assert len(rec.signals) == 9  # 9 signals now

    def test_with_historical_context(self):
        contracts = make_contracts()
        analytics = make_analytics()
        gamma = make_gamma_levels()
        hist = {
            'gex_percentile': 0.85,
            'momentum': {'gex_trend': 0.3, 'gex_samples': 5, 'gex_start': 100, 'gex_end': 130},
            'iv_rank': 0.75,
            'previous_pc_ratio': 1.1,
        }
        rec = score_ticker('SPY', contracts, analytics, gamma, hist)
        assert rec.score > 0
        assert rec.iv_rank_value == 0.75
        assert rec.price_at_score > 0

    def test_empty_data(self):
        rec = score_ticker('SPY', [], {}, {})
        assert rec.score <= 10  # small base from neutral defaults (IV rank, DTE)
        assert rec.ticker == 'SPY'

    def test_has_reasoning(self):
        contracts = make_contracts()
        analytics = make_analytics()
        gamma = make_gamma_levels()
        rec = score_ticker('SPY', contracts, analytics, gamma)
        assert len(rec.reasoning) > 10
        assert len(rec.risk_notes) > 0


class TestScoreAllTickers:
    def test_multiple_tickers(self):
        contracts = make_contracts('SPY') + make_contracts('QQQ', price=500)
        analytics = {'SPY': make_analytics(590), 'QQQ': make_analytics(500)}
        gamma = {
            'SPY': make_gamma_levels(),
            'QQQ': make_gamma_levels(505, 490),
        }
        recs = score_all_tickers(contracts, analytics, gamma)
        assert len(recs) == 2
        assert recs[0].score >= recs[1].score

    def test_empty_data(self):
        recs = score_all_tickers([], {}, {})
        assert recs == []

    def test_to_dict(self):
        contracts = make_contracts()
        analytics = make_analytics()
        gamma = make_gamma_levels()
        rec = score_ticker('SPY', contracts, analytics, gamma)
        d = rec.to_dict()
        assert isinstance(d, dict)
        assert d['ticker'] == 'SPY'
        assert 'score' in d
        assert 'signals' in d
        assert 'price_at_score' in d
        assert 'iv_rank_value' in d

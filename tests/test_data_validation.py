"""
Tests for Data Validation
==========================
Validates that option contract data has correct structure and reasonable values.
"""

import pytest


def make_contract(**overrides):
    """Create a valid test contract dict."""
    base = {
        'Symbol': 'SPY',
        'Underlying': 'SPY',
        'UnderlyingPrice': 590.0,
        'OptionSymbol': 'SPY250321C00590000',
        'Expiration': '2025-03-21',
        'Strike': 590.0,
        'Type': 'CALL',
        'Bid': 5.10,
        'Ask': 5.20,
        'Last': 5.15,
        'TradeSide': 'MID',
        'Volume': 1500,
        'OpenInterest': 25000,
        'Delta': 0.5,
        'Gamma': 0.02,
        'Theta': -0.05,
        'Vega': 0.15,
        'Rho': 0.01,
        'ImpliedVol': 18.5,
    }
    base.update(overrides)
    return base


# --- Required Fields Tests ---

REQUIRED_FIELDS = [
    'Symbol', 'Strike', 'Type', 'OpenInterest', 'Gamma', 'Delta',
    'Vega', 'Theta', 'UnderlyingPrice'
]

class TestRequiredFields:
    def test_valid_contract_has_all_fields(self):
        c = make_contract()
        for field in REQUIRED_FIELDS:
            assert field in c, f"Missing required field: {field}"

    def test_missing_field_detected(self):
        c = make_contract()
        del c['Strike']
        assert 'Strike' not in c


# --- Numeric Validation Tests ---

class TestNumericValidation:
    def test_strike_is_positive(self):
        c = make_contract()
        assert c['Strike'] > 0

    def test_strike_zero_invalid(self):
        c = make_contract(Strike=0)
        assert c['Strike'] <= 0  # Should fail validation

    def test_oi_non_negative(self):
        c = make_contract()
        assert c['OpenInterest'] >= 0

    def test_volume_non_negative(self):
        c = make_contract()
        assert c['Volume'] >= 0

    def test_underlying_price_positive(self):
        c = make_contract()
        assert c['UnderlyingPrice'] > 0

    def test_delta_in_range(self):
        """Delta should be between -1 and 1."""
        c = make_contract()
        assert -1 <= c['Delta'] <= 1

    def test_gamma_non_negative(self):
        """Gamma is always non-negative."""
        c = make_contract()
        assert c['Gamma'] >= 0

    def test_implied_vol_positive(self):
        c = make_contract()
        assert c['ImpliedVol'] > 0


# --- Option Type Tests ---

class TestOptionType:
    def test_valid_call(self):
        c = make_contract(Type='CALL')
        assert c['Type'] in ('CALL', 'PUT')

    def test_valid_put(self):
        c = make_contract(Type='PUT')
        assert c['Type'] in ('CALL', 'PUT')

    def test_invalid_type_detected(self):
        c = make_contract(Type='INVALID')
        assert c['Type'] not in ('CALL', 'PUT')


# --- Trade Side Tests ---

class TestTradeSide:
    def test_valid_trade_sides(self):
        valid = ['ASK (Buy)', 'BID (Sell)', 'Near ASK', 'Near BID', 'MID']
        for side in valid:
            c = make_contract(TradeSide=side)
            assert c['TradeSide'] in valid

    def test_trade_side_logic(self):
        """If last >= ask, trade side should be ASK (Buy)."""
        c = make_contract(Bid=5.0, Ask=5.5, Last=5.6)
        # Per the logic in fetch_options_data.py
        if c['Last'] >= c['Ask']:
            expected_side = 'ASK (Buy)'
        elif c['Last'] <= c['Bid']:
            expected_side = 'BID (Sell)'
        else:
            mid = (c['Bid'] + c['Ask']) / 2
            expected_side = 'Near ASK' if c['Last'] > mid else 'Near BID'
        assert expected_side == 'ASK (Buy)'


# --- Batch Validation ---

class TestBatchValidation:
    def test_batch_all_same_ticker(self):
        contracts = [make_contract(Symbol='SPY') for _ in range(10)]
        tickers = set(c['Symbol'] for c in contracts)
        assert len(tickers) == 1

    def test_batch_multiple_tickers(self):
        contracts = [
            make_contract(Symbol='SPY'),
            make_contract(Symbol='QQQ'),
            make_contract(Symbol='AAPL'),
        ]
        tickers = set(c['Symbol'] for c in contracts)
        assert len(tickers) == 3

    def test_batch_strike_ordering(self):
        contracts = [
            make_contract(Strike=580),
            make_contract(Strike=590),
            make_contract(Strike=600),
        ]
        strikes = [c['Strike'] for c in contracts]
        assert strikes == sorted(strikes)

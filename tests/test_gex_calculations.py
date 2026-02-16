"""
Tests for GEX Calculations
============================
Verifies Gamma Exposure formulas and star level computation against known values.
"""

import pytest


def compute_gex(gamma, oi, spot_price, option_type):
    """Compute GEX for a single contract (matches extract_gamma_levels.py logic).
    
    Formula: Gamma × OI × 100 × SpotPrice² × 0.01
    Calls contribute positive GEX, puts contribute negative GEX.
    """
    exposure = gamma * oi * 100 * spot_price * spot_price * 0.01
    if option_type == 'CALL':
        return exposure
    elif option_type == 'PUT':
        return -exposure
    return 0


def compute_net_gex_simple(gamma, oi, spot_price, option_type):
    """Simplified GEX used in analytics: Gamma × OI × 100 × SpotPrice."""
    gex = gamma * oi * 100 * spot_price
    if option_type == 'PUT':
        gex = -gex
    return gex


class TestGexFormula:
    """Test the GEX formula with known inputs."""

    def test_call_positive_gex(self):
        """Call options should produce positive GEX."""
        gex = compute_gex(gamma=0.02, oi=10000, spot_price=590, option_type='CALL')
        assert gex > 0

    def test_put_negative_gex(self):
        """Put options should produce negative GEX."""
        gex = compute_gex(gamma=0.02, oi=10000, spot_price=590, option_type='PUT')
        assert gex < 0

    def test_call_put_symmetry(self):
        """Call and put with same inputs should have equal magnitude."""
        call_gex = compute_gex(0.02, 10000, 590, 'CALL')
        put_gex = compute_gex(0.02, 10000, 590, 'PUT')
        assert abs(call_gex) == abs(put_gex)
        assert call_gex == -put_gex

    def test_known_values(self):
        """Verify GEX calculation with hand-calculated values.
        gamma=0.02, oi=10000, spot=500
        GEX = 0.02 * 10000 * 100 * 500^2 * 0.01
            = 0.02 * 10000 * 100 * 250000 * 0.01
            = 0.02 * 10000 * 100 * 2500
            = 50,000,000
        """
        gex = compute_gex(0.02, 10000, 500, 'CALL')
        assert gex == pytest.approx(50_000_000, rel=1e-6)

    def test_zero_gamma_produces_zero(self):
        gex = compute_gex(0, 10000, 590, 'CALL')
        assert gex == 0

    def test_zero_oi_produces_zero(self):
        gex = compute_gex(0.02, 0, 590, 'CALL')
        assert gex == 0

    def test_gex_scales_with_spot_squared(self):
        """GEX should scale quadratically with spot price."""
        gex_100 = compute_gex(0.02, 100, 100, 'CALL')
        gex_200 = compute_gex(0.02, 100, 200, 'CALL')
        assert gex_200 == pytest.approx(gex_100 * 4, rel=1e-6)

    def test_gex_scales_linearly_with_oi(self):
        gex_1k = compute_gex(0.02, 1000, 500, 'CALL')
        gex_2k = compute_gex(0.02, 2000, 500, 'CALL')
        assert gex_2k == pytest.approx(gex_1k * 2, rel=1e-6)


class TestStarLevelComputation:
    """Test the logic for finding max positive/negative GEX strikes."""

    def _find_star_levels(self, contracts):
        """Simplified version of compute_star_levels."""
        cell_gex = {}  # strike -> net GEX

        for c in contracts:
            strike = c['strike']
            gex = compute_gex(c['gamma'], c['oi'], c['spot'], c['type'])
            cell_gex[strike] = cell_gex.get(strike, 0) + gex

        max_pos_strike = None
        max_pos_gex = -float('inf')
        max_neg_strike = None
        max_neg_gex = float('inf')

        for strike, gex in cell_gex.items():
            if gex > 0 and gex > max_pos_gex:
                max_pos_gex = gex
                max_pos_strike = strike
            if gex < 0 and gex < max_neg_gex:
                max_neg_gex = gex
                max_neg_strike = strike

        return max_pos_strike, max_neg_strike

    def test_simple_star_levels(self):
        contracts = [
            {'strike': 590, 'gamma': 0.05, 'oi': 50000, 'spot': 590, 'type': 'CALL'},
            {'strike': 580, 'gamma': 0.03, 'oi': 30000, 'spot': 590, 'type': 'PUT'},
            {'strike': 600, 'gamma': 0.02, 'oi': 20000, 'spot': 590, 'type': 'CALL'},
        ]
        pos, neg = self._find_star_levels(contracts)
        assert pos == 590  # Highest call GEX
        assert neg == 580  # Only put

    def test_no_puts_no_negative_star(self):
        contracts = [
            {'strike': 590, 'gamma': 0.05, 'oi': 50000, 'spot': 590, 'type': 'CALL'},
            {'strike': 600, 'gamma': 0.02, 'oi': 20000, 'spot': 590, 'type': 'CALL'},
        ]
        pos, neg = self._find_star_levels(contracts)
        assert pos is not None
        assert neg is None

    def test_mixed_same_strike(self):
        """When calls and puts exist at the same strike, net determines the star."""
        contracts = [
            {'strike': 590, 'gamma': 0.05, 'oi': 50000, 'spot': 590, 'type': 'CALL'},
            {'strike': 590, 'gamma': 0.08, 'oi': 80000, 'spot': 590, 'type': 'PUT'},
        ]
        pos, neg = self._find_star_levels(contracts)
        # Net GEX at 590 should be negative (put > call)
        assert neg == 590

    def test_empty_contracts(self):
        pos, neg = self._find_star_levels([])
        assert pos is None
        assert neg is None

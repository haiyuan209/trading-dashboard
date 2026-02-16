"""
Tests for Alert Detection Logic
=================================
Verifies GEX flip, max strike shift, and price-near-wall detection.
"""

import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alerts.detector import (
    detect_gex_flip,
    detect_new_max_strike,
    detect_price_near_wall,
    run_all_checks,
    Alert,
)


class TestGexFlipDetection:
    def test_positive_to_negative_flip(self):
        alert = detect_gex_flip('SPY', current_net_gex=-500000, previous_net_gex=300000)
        assert alert is not None
        assert alert.severity == 'critical'
        assert alert.alert_type == 'gex_flip'
        assert 'NEGATIVE' in alert.message

    def test_negative_to_positive_flip(self):
        alert = detect_gex_flip('SPY', current_net_gex=300000, previous_net_gex=-500000)
        assert alert is not None
        assert alert.severity == 'warning'
        assert 'POSITIVE' in alert.message

    def test_no_flip_same_sign(self):
        alert = detect_gex_flip('SPY', current_net_gex=100000, previous_net_gex=200000)
        assert alert is None

    def test_no_flip_both_negative(self):
        alert = detect_gex_flip('SPY', current_net_gex=-100000, previous_net_gex=-200000)
        assert alert is None

    def test_none_previous_no_alert(self):
        alert = detect_gex_flip('SPY', current_net_gex=100000, previous_net_gex=None)
        assert alert is None

    def test_none_current_no_alert(self):
        alert = detect_gex_flip('SPY', current_net_gex=None, previous_net_gex=100000)
        assert alert is None


class TestMaxStrikeDetection:
    def test_positive_strike_shift(self):
        alerts = detect_new_max_strike('SPY', 595, 580, 590, 580)
        assert len(alerts) == 1
        assert 'Call wall shifted' in alerts[0].message

    def test_negative_strike_shift(self):
        alerts = detect_new_max_strike('SPY', 590, 575, 590, 580)
        assert len(alerts) == 1
        assert 'Put wall shifted' in alerts[0].message

    def test_both_shifts(self):
        alerts = detect_new_max_strike('SPY', 595, 575, 590, 580)
        assert len(alerts) == 2

    def test_no_shift(self):
        alerts = detect_new_max_strike('SPY', 590, 580, 590, 580)
        assert len(alerts) == 0

    def test_none_values_no_alert(self):
        alerts = detect_new_max_strike('SPY', None, None, None, None)
        assert len(alerts) == 0


class TestPriceNearWall:
    def test_price_near_call_wall(self):
        alerts = detect_price_near_wall('SPY', price=589.5, pos_strike=590, neg_strike=580, threshold_pct=1.0)
        assert len(alerts) == 1
        assert 'call wall' in alerts[0].message

    def test_price_near_put_wall(self):
        alerts = detect_price_near_wall('SPY', price=580.5, pos_strike=600, neg_strike=580, threshold_pct=1.0)
        assert len(alerts) == 1
        assert 'put wall' in alerts[0].message

    def test_price_far_from_walls(self):
        alerts = detect_price_near_wall('SPY', price=590, pos_strike=610, neg_strike=570, threshold_pct=1.0)
        assert len(alerts) == 0

    def test_zero_price_no_alert(self):
        alerts = detect_price_near_wall('SPY', price=0, pos_strike=590, neg_strike=580)
        assert len(alerts) == 0


class TestRunAllChecks:
    def test_no_previous_data(self):
        current = {'SPY': {'price': 590, 'max_positive_gamma_strike': 595,
                           'max_negative_gamma_strike': 580,
                           'max_positive_gamma_value': 1000, 'max_negative_gamma_value': -500}}
        alerts = run_all_checks(current, None)
        # Should still run price-near-wall checks
        assert isinstance(alerts, list)

    def test_unchanged_data_no_alerts(self):
        data = {'SPY': {'price': 590, 'max_positive_gamma_strike': 610,
                        'max_negative_gamma_strike': 570,
                        'max_positive_gamma_value': 1000, 'max_negative_gamma_value': -500}}
        alerts = run_all_checks(data, data, threshold_pct=0.5)
        # No flips, no shifts, price far from walls
        assert len(alerts) == 0

    def test_severity_ordering(self):
        current = {'SPY': {'price': 590, 'max_positive_gamma_strike': 591,
                           'max_negative_gamma_strike': 580,
                           'max_positive_gamma_value': -100, 'max_negative_gamma_value': -500}}
        previous = {'SPY': {'price': 590, 'max_positive_gamma_strike': 595,
                            'max_negative_gamma_strike': 575,
                            'max_positive_gamma_value': 100, 'max_negative_gamma_value': -500}}
        alerts = run_all_checks(current, previous, threshold_pct=1.0)
        # Should be sorted: critical first
        if len(alerts) > 1:
            sev = {'critical': 0, 'warning': 1, 'info': 2}
            for i in range(len(alerts) - 1):
                assert sev[alerts[i].severity] <= sev[alerts[i+1].severity]

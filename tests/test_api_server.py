"""
Tests for API Server Endpoints
================================
Uses FastAPI TestClient to verify REST endpoints.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from api_server import app, _data_store


@pytest.fixture(autouse=True)
def setup_test_data():
    """Seed the in-memory store with test data."""
    _data_store['option_data'] = [
        {'Symbol': 'SPY', 'Strike': 590, 'Type': 'CALL', 'OpenInterest': 10000,
         'Gamma': 0.02, 'Delta': 0.5, 'UnderlyingPrice': 590},
        {'Symbol': 'SPY', 'Strike': 590, 'Type': 'PUT', 'OpenInterest': 8000,
         'Gamma': 0.018, 'Delta': -0.5, 'UnderlyingPrice': 590},
        {'Symbol': 'QQQ', 'Strike': 500, 'Type': 'CALL', 'OpenInterest': 5000,
         'Gamma': 0.015, 'Delta': 0.45, 'UnderlyingPrice': 500},
    ]
    _data_store['analytics_data'] = {
        'data': {
            'SPY': {'price': 590, 'strikes': {590: {'total_gamma': 0.02, 'oi': 18000}}},
            'QQQ': {'price': 500, 'strikes': {500: {'total_gamma': 0.015, 'oi': 5000}}},
        },
        'metadata': {'total_tickers': 2}
    }
    _data_store['gamma_levels'] = {
        'SPY': {'max_positive_gamma_strike': 595, 'max_negative_gamma_strike': 580}
    }
    _data_store['last_updated'] = '2026-02-15T10:00:00'
    yield


client = TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_ok(self):
        resp = client.get('/api/health')
        assert resp.status_code == 200
        data = resp.json()
        assert data['status'] == 'ok'
        assert 'last_updated' in data

    def test_health_has_counts(self):
        resp = client.get('/api/health')
        data = resp.json()
        assert data['contracts'] == 3
        assert data['tickers'] == 2


class TestTickersEndpoint:
    def test_list_tickers(self):
        resp = client.get('/api/tickers')
        assert resp.status_code == 200
        tickers = resp.json()['tickers']
        assert 'SPY' in tickers
        assert 'QQQ' in tickers


class TestOptionsEndpoint:
    def test_get_spy_options(self):
        resp = client.get('/api/options/SPY')
        assert resp.status_code == 200
        data = resp.json()
        assert data['ticker'] == 'SPY'
        assert data['count'] == 2

    def test_unknown_ticker_404(self):
        resp = client.get('/api/options/ZZZZZ')
        assert resp.status_code == 404


class TestAnalyticsEndpoint:
    def test_get_spy_analytics(self):
        resp = client.get('/api/analytics/SPY')
        assert resp.status_code == 200
        data = resp.json()
        assert data['ticker'] == 'SPY'
        assert 'data' in data

    def test_unknown_ticker_404(self):
        resp = client.get('/api/analytics/ZZZZZ')
        assert resp.status_code == 404


class TestGammaLevelsEndpoint:
    def test_all_gamma_levels(self):
        resp = client.get('/api/gamma-levels')
        assert resp.status_code == 200
        data = resp.json()
        assert 'SPY' in data

    def test_spy_gamma_levels(self):
        resp = client.get('/api/gamma-levels/SPY')
        assert resp.status_code == 200
        data = resp.json()
        assert data['ticker'] == 'SPY'


class TestCorsHeaders:
    def test_cors_present(self):
        resp = client.options('/api/health', headers={
            'Origin': 'http://localhost:3000',
            'Access-Control-Request-Method': 'GET'
        })
        # CORS middleware should allow all origins
        assert resp.status_code == 200


class TestMetadataEndpoint:
    def test_metadata(self):
        resp = client.get('/api/metadata')
        assert resp.status_code == 200

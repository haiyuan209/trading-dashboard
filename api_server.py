"""
FastAPI REST Server for Options Dashboard
==========================================
Serves options data via REST endpoints, replacing static 95MB JS file loading.
Also serves the dashboard HTML as a static file.

Usage:
    python api_server.py
    → Dashboard at http://localhost:8000
    → API at http://localhost:8000/api/...
"""

import os
import json
import re
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from logger import get_logger
from config import load_config

log = get_logger("api_server")

app = FastAPI(title="Options Trading Dashboard API", version="2.0")

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- In-memory data store (refreshed by fetcher) ---
_data_store = {
    "option_data": [],
    "analytics_data": {},
    "gamma_levels": {},
    "metadata": {},
    "recommendations": {},
    "last_updated": None,
}

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_js_data(filepath: str, var_name: str):
    """Parse a JS file like 'const VAR_NAME = {...};' into Python."""
    full_path = os.path.join(PROJECT_DIR, filepath)
    if not os.path.exists(full_path):
        return None
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        pattern = rf'const\s+{var_name}\s*=\s*(\[.*\]|{{.*}})\s*;'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            return json.loads(match.group(1))
    except Exception as e:
        log.warning("Failed to parse %s: %s", filepath, e)
    return None


def refresh_data_store():
    """Reload data from JS files into memory. Called after each fetch cycle."""
    # Option data (heatmap)
    option_data = _load_js_data('option_data.js', 'OPTION_DATA')
    if option_data:
        _data_store['option_data'] = option_data

    # Analytics data
    analytics_data = _load_js_data('all_tickers_data.js', 'TICKER_DATA')
    if analytics_data:
        _data_store['analytics_data'] = analytics_data

    # Gamma levels
    gamma_path = os.path.join(PROJECT_DIR, 'gamma_levels.json')
    if os.path.exists(gamma_path):
        try:
            with open(gamma_path, 'r', encoding='utf-8') as f:
                _data_store['gamma_levels'] = json.load(f)
        except Exception:
            pass

    # Metadata
    meta_path = os.path.join(PROJECT_DIR, 'fetch_metadata.json')
    if os.path.exists(meta_path):
        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                _data_store['metadata'] = json.load(f)
        except Exception:
            pass

    # Recommendations
    recs_path = os.path.join(PROJECT_DIR, 'recommendations.json')
    if os.path.exists(recs_path):
        try:
            with open(recs_path, 'r', encoding='utf-8') as f:
                _data_store['recommendations'] = json.load(f)
        except Exception:
            pass

    _data_store['last_updated'] = datetime.now().isoformat()
    log.info("Data store refreshed: %d contracts, %d tickers",
             len(_data_store['option_data']),
             len(_data_store.get('analytics_data', {}).get('data', {})))


# --- API Endpoints ---


@app.get("/api/health")
def health():
    """Health check with last update time."""
    return {
        "status": "ok",
        "last_updated": _data_store['last_updated'],
        "contracts": len(_data_store['option_data']),
        "tickers": len(_data_store.get('analytics_data', {}).get('data', {})),
    }


@app.get("/api/tickers")
def list_tickers():
    """List all available tickers."""
    analytics = _data_store.get('analytics_data', {})
    tickers = list(analytics.get('data', {}).keys()) if analytics else []
    if not tickers:
        tickers = sorted(set(c.get('Symbol', '') for c in _data_store['option_data'] if c.get('Symbol')))
    return {"tickers": tickers}


@app.get("/api/options/{ticker}")
def get_options(ticker: str):
    """Get option contracts for a specific ticker (for heatmap)."""
    ticker = ticker.upper()
    contracts = [c for c in _data_store['option_data'] if c.get('Symbol') == ticker]
    if not contracts:
        raise HTTPException(status_code=404, detail=f"No data for ticker {ticker}")
    return {"ticker": ticker, "contracts": contracts, "count": len(contracts)}


@app.get("/api/analytics/{ticker}")
def get_analytics(ticker: str):
    """Get aggregated strike-level analytics for a ticker."""
    ticker = ticker.upper()
    analytics = _data_store.get('analytics_data', {})
    data = analytics.get('data', {}).get(ticker)
    if not data:
        raise HTTPException(status_code=404, detail=f"No analytics data for {ticker}")
    return {"ticker": ticker, "data": data}


@app.get("/api/gamma-levels")
def get_all_gamma_levels():
    """Get gamma star levels for all tickers."""
    return _data_store.get('gamma_levels', {})


@app.get("/api/gamma-levels/{ticker}")
def get_ticker_gamma_levels(ticker: str):
    """Get gamma levels for a specific ticker."""
    ticker = ticker.upper()
    levels = _data_store.get('gamma_levels', {}).get(ticker)
    if not levels:
        raise HTTPException(status_code=404, detail=f"No gamma levels for {ticker}")
    return {"ticker": ticker, **levels}


@app.get("/api/history/{ticker}")
def get_history(ticker: str, hours: int = Query(default=24, ge=1, le=168)):
    """Get historical gamma level data from SQLite."""
    ticker = ticker.upper()
    try:
        from db.queries import get_gamma_history
        history = get_gamma_history(ticker, hours)
        return {"ticker": ticker, "hours": hours, "data": history}
    except Exception as e:
        log.warning("History query failed: %s", e)
        return {"ticker": ticker, "hours": hours, "data": []}


@app.get("/api/oi-change/{ticker}")
def get_oi_change(ticker: str, interval: int = Query(default=60, ge=1, le=1440)):
    """Get OI change data for unusual activity detection."""
    ticker = ticker.upper()
    try:
        from db.queries import get_oi_change as query_oi_change
        changes = query_oi_change(ticker, interval_minutes=interval)
        # Return top 20 biggest changes
        return {"ticker": ticker, "interval_minutes": interval, "changes": changes[:20]}
    except Exception as e:
        log.warning("OI change query failed: %s", e)
        return {"ticker": ticker, "interval_minutes": interval, "changes": []}


@app.get("/api/alerts/recent")
def get_recent_alerts(hours: int = Query(default=24, ge=1, le=168)):
    """Get recent alerts from the database."""
    try:
        from db.queries import get_recent_alerts
        alerts = get_recent_alerts(hours=hours)
        return {"hours": hours, "alerts": alerts}
    except Exception as e:
        log.warning("Alerts query failed: %s", e)
        return {"hours": hours, "alerts": []}


@app.get("/api/metadata")
def get_metadata():
    """Get fetch metadata (last update time, errors, etc)."""
    return _data_store.get('metadata', {})


@app.get("/api/recommendations")
def get_recommendations():
    """Get all trade recommendations sorted by score."""
    recs = _data_store.get('recommendations', {})
    return recs if recs else {"recommendations": [], "disclaimer": "No recommendations yet."}


@app.get("/api/recommendations/backtest")
def backtest_recommendations(hours: int = Query(default=24, ge=1, le=168)):
    """Evaluate past recommendation accuracy using real Schwab price data."""
    try:
        from agent.backtester import evaluate_recommendations
        return evaluate_recommendations(hours=hours)
    except Exception as e:
        log.warning("Backtest failed: %s", e)
        return {"error": str(e), "total_recommendations": 0}


@app.get("/api/recommendations/{ticker}")
def get_ticker_recommendation(ticker: str):
    """Get recommendation for a specific ticker."""
    ticker = ticker.upper()
    recs = _data_store.get('recommendations', {}).get('recommendations', [])
    for r in recs:
        if r.get('ticker') == ticker:
            return r
    raise HTTPException(status_code=404, detail=f"No recommendation for {ticker}")


# --- Serve static files (dashboard) ---

@app.get("/", response_class=HTMLResponse)
def serve_dashboard():
    """Serve the dashboard HTML."""
    html_path = os.path.join(PROJECT_DIR, 'unified_dashboard.html')
    if os.path.exists(html_path):
        with open(html_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "<h1>Dashboard not found</h1>"


# Serve JS/CSS files from project directory
@app.get("/{filename:path}")
def serve_static(filename: str):
    """Serve static files from project directory."""
    filepath = os.path.join(PROJECT_DIR, filename)
    if os.path.exists(filepath) and os.path.isfile(filepath):
        return FileResponse(filepath)
    raise HTTPException(status_code=404, detail="File not found")


# --- Startup ---

@app.on_event("startup")
def startup():
    """Load data on server start."""
    from db.models import init_db
    try:
        init_db()
    except Exception as e:
        log.warning("Database init failed: %s", e)
    refresh_data_store()


if __name__ == "__main__":
    import uvicorn
    cfg = load_config()
    log.info("Starting API server on %s:%d", cfg.api_server.host, cfg.api_server.port)
    refresh_data_store()
    uvicorn.run(
        "api_server:app",
        host=cfg.api_server.host,
        port=cfg.api_server.port,
        reload=False,
        log_level="info"
    )

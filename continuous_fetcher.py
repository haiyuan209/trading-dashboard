"""
Continuous Data Fetcher - Runs every minute
Fetches options data for all tickers and updates dashboard files.
Now integrates: config, structured logging, historical DB, alerts, API refresh.
"""

import time
import json
from datetime import datetime
from ticker_list import TOP_100_LIQUID_OPTIONS
from fetch_options_data import get_client, fetch_option_data
from logger import get_logger
from config import load_config
import os

log = get_logger("continuous_fetcher")
cfg = load_config()

REFRESH_INTERVAL = cfg.fetcher.refresh_interval
MAX_TICKERS_PER_CYCLE = cfg.fetcher.max_tickers_per_cycle

# Store previous gamma data for alert comparisons
_previous_gamma_data = None


def save_option_data(all_data):
    """Save options data to JavaScript file for dashboard"""
    timestamp = datetime.now().isoformat()

    # Generate JavaScript file
    js_content = f"// Auto-generated at {timestamp}\nconst OPTION_DATA = {json.dumps(all_data, indent=2)};\n"

    with open('option_data.js', 'w', encoding='utf-8') as f:
        f.write(js_content)

    log.info("Saved %d contracts to option_data.js", len(all_data))

def save_analytics_data(all_data):
    """Generate analytics data (all_tickers_data.js) from options data"""
    timestamp = datetime.now().isoformat()

    # Aggregate data by ticker and strike for analytics view
    ticker_data = {}

    for contract in all_data:
        ticker = contract['Symbol']
        strike = contract['Strike']
        underlying_price = contract['UnderlyingPrice']

        if ticker not in ticker_data:
            ticker_data[ticker] = {
                'price': underlying_price,
                'timestamp': timestamp,
                'strikes': {}
            }

        if strike not in ticker_data[ticker]['strikes']:
            ticker_data[ticker]['strikes'][strike] = {
                'total_delta': 0,
                'total_gamma': 0,
                'total_theta': 0,
                'total_vega': 0,
                'oi': 0,
                'volume': 0
            }

        # Aggregate Greeks weighted by open interest
        oi = contract.get('OpenInterest', 0)
        volume = contract.get('Volume', 0)

        ticker_data[ticker]['strikes'][strike]['total_delta'] += (contract.get('Delta', 0) * oi)
        ticker_data[ticker]['strikes'][strike]['total_gamma'] += (contract.get('Gamma', 0) * oi)
        ticker_data[ticker]['strikes'][strike]['total_theta'] += (contract.get('Theta', 0) * oi)
        ticker_data[ticker]['strikes'][strike]['total_vega'] += (contract.get('Vega', 0) * oi)
        ticker_data[ticker]['strikes'][strike]['oi'] += oi
        ticker_data[ticker]['strikes'][strike]['volume'] += volume

    # Build output structure
    output = {
        'metadata': {
            'total_tickers': len(ticker_data),
            'generated_at': timestamp,
            'tickers': list(ticker_data.keys())
        },
        'data': ticker_data
    }

    # Save as JavaScript file
    js_content = f"// Auto-generated ticker data\n// Generated: {timestamp}\n// Total tickers: {len(ticker_data)}\n\n"
    js_content += f"const TICKER_DATA = {json.dumps(output, indent=2)};\n"

    with open('all_tickers_data.js', 'w', encoding='utf-8') as f:
        f.write(js_content)

    log.info("Saved %d tickers to all_tickers_data.js", len(ticker_data))

def save_metadata(ticker_count, contract_count, errors):
    """Save fetch metadata"""
    metadata = {
        'last_updated': datetime.now().isoformat(),
        'tickers_processed': ticker_count,
        'contracts_fetched': contract_count,
        'errors': len(errors),
        'error_tickers': errors
    }

    with open('fetch_metadata.json', 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)

    log.info("Updated metadata")

def save_price_history(all_data):
    """Accumulate price history for chart view (Lightweight Charts candlestick data).

    Each fetch cycle appends a new data point per ticker with the current price.
    Old data (>5 days) is pruned automatically. Output: price_history.js
    """
    import math
    timestamp = datetime.now().isoformat()
    # Unix timestamp in seconds for Lightweight Charts
    unix_ts = int(datetime.now().timestamp())

    # Extract current price per ticker
    ticker_prices = {}
    for contract in all_data:
        ticker = contract.get('Symbol', '')
        price = contract.get('UnderlyingPrice', 0)
        if ticker and price > 0:
            ticker_prices[ticker] = price

    # Load existing history
    history_file = 'price_history.json'
    history = {}
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
        except (json.JSONDecodeError, IOError):
            history = {}

    # Prune old data (keep last 5 days = 432000 seconds)
    cutoff = unix_ts - 432000

    for ticker, price in ticker_prices.items():
        if ticker not in history:
            history[ticker] = []

        # Append new data point
        history[ticker].append({
            'time': unix_ts,
            'value': round(price, 2)
        })

        # Prune old entries
        history[ticker] = [p for p in history[ticker] if p['time'] > cutoff]

    # Save as JSON
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(history, f)

    # Also save as JS for direct browser loading
    js_content = f"// Auto-generated price history at {timestamp}\nconst PRICE_HISTORY = {json.dumps(history)};\n"
    with open('price_history.js', 'w', encoding='utf-8') as f:
        f.write(js_content)

    log.info("Saved price history for %d tickers", len(ticker_prices))


def _run_historical_storage(all_data):
    """Save snapshot to SQLite database."""
    try:
        from db.storage import save_snapshot, prune_old_data
        save_snapshot(all_data)
        prune_old_data()  # Clean up old data based on config
    except Exception as e:
        log.warning("Historical storage failed: %s", e)


def _run_alert_checks(gamma_data):
    """Run alert detection and dispatch notifications."""
    global _previous_gamma_data

    if not cfg.alerts.enabled:
        return

    try:
        from alerts.detector import run_all_checks
        from alerts.notifier import dispatch_alerts
        from db.storage import save_gamma_snapshot

        # Save gamma levels to DB
        save_gamma_snapshot(gamma_data)

        # Run alert checks
        thresholds = cfg.alerts.thresholds
        alerts = run_all_checks(
            current_data=gamma_data,
            previous_data=_previous_gamma_data,
            threshold_pct=thresholds.price_near_gamma_wall_pct,
            check_gex_flip=thresholds.gex_flip,
            check_max_strike=thresholds.new_max_gamma_strike,
        )

        if alerts:
            dispatch_alerts(alerts)

        _previous_gamma_data = gamma_data

    except Exception as e:
        log.warning("Alert checks failed: %s", e)


def _run_recommendations(all_data, gamma_data):
    """Run trade recommendation agent on current data."""
    try:
        from agent.scorer import score_all_tickers, save_recommendations

        # Build analytics dict from raw contracts
        analytics = {}
        for c in all_data:
            ticker = c.get('Symbol', '')
            strike = c.get('Strike', 0)
            if not ticker:
                continue
            if ticker not in analytics:
                analytics[ticker] = {
                    'price': c.get('UnderlyingPrice', 0),
                    'strikes': {}
                }
            if strike not in analytics[ticker]['strikes']:
                analytics[ticker]['strikes'][strike] = {
                    'total_gamma': 0, 'total_delta': 0,
                    'total_vega': 0, 'total_theta': 0,
                    'oi': 0, 'volume': 0
                }
            oi = c.get('OpenInterest', 0) or 0
            sd = analytics[ticker]['strikes'][strike]
            sd['total_gamma'] += (c.get('Gamma', 0) * oi)
            sd['total_delta'] += (c.get('Delta', 0) * oi)
            sd['total_vega']  += (c.get('Vega', 0) * oi)
            sd['total_theta'] += (c.get('Theta', 0) * oi)
            sd['oi'] += oi
            sd['volume'] += (c.get('Volume', 0) or 0)

        recs = score_all_tickers(all_data, analytics, gamma_data or {})
        save_recommendations(recs)
        log.info("Generated %d trade recommendations", len(recs))
    except Exception as e:
        log.warning("Recommendation agent failed: %s", e)


def _refresh_api_store():
    """Refresh the in-memory API data store if the server is running."""
    try:
        from api_server import refresh_data_store
        refresh_data_store()
    except Exception:
        pass  # API server not running, that's fine


def fetch_all_tickers():
    """Fetch data for all tickers using parallel workers"""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    log.info("=" * 70)
    log.info("Data Fetch Cycle Started: %s", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    log.info("=" * 70)

    client = get_client()
    if not client:
        log.error("Could not initialize Schwab client")
        return

    all_data = []
    errors = []

    # Limit tickers to avoid overwhelming API
    tickers_to_fetch = TOP_100_LIQUID_OPTIONS[:MAX_TICKERS_PER_CYCLE]
    total_tickers = len(tickers_to_fetch)
    PARALLEL_WORKERS = 10

    log.info("Fetching %d tickers with %d parallel workers...", total_tickers, PARALLEL_WORKERS)
    start_time = time.time()

    def _fetch_one(ticker):
        try:
            ticker_data = fetch_option_data(client, ticker)
            return ticker, ticker_data or []
        except Exception as e:
            log.error("  Error fetching %s: %s", ticker, e)
            return ticker, []

    with ThreadPoolExecutor(max_workers=PARALLEL_WORKERS) as executor:
        futures = {executor.submit(_fetch_one, t): t for t in tickers_to_fetch}

        for future in as_completed(futures):
            ticker = futures[future]
            try:
                _, ticker_data = future.result()
                if ticker_data:
                    all_data.extend(ticker_data)
                else:
                    errors.append(ticker)
            except Exception as e:
                log.error("Future error for %s: %s", ticker, e)
                errors.append(ticker)

    elapsed = time.time() - start_time
    log.info("Fetched %d contracts in %.1fs (%d errors)", len(all_data), elapsed, len(errors))

    # Save data files (existing behavior)
    log.info("=" * 70)
    log.info("Saving data...")
    log.info("=" * 70)

    save_option_data(all_data)      # For heatmap view
    save_analytics_data(all_data)   # For analytics view
    save_metadata(len(tickers_to_fetch), len(all_data), errors)
    save_price_history(all_data)    # For chart view

    # --- NEW: Historical database storage ---
    _run_historical_storage(all_data)

    # Auto-generate gamma star levels + alerts
    gamma_data = None
    try:
        from extract_gamma_levels import run_extraction
        log.info("Generating gamma star levels...")
        gamma_data = run_extraction()
    except Exception as e:
        log.warning("Could not generate gamma levels: %s", e)

    # --- NEW: Alert checks ---
    if gamma_data:
        _run_alert_checks(gamma_data)

    # --- NEW: Trade recommendations ---
    _run_recommendations(all_data, gamma_data)

    # --- NEW: Refresh API server data store ---
    _refresh_api_store()

    log.info("Fetch cycle complete — %d contracts, %d errors", len(all_data), len(errors))
    if errors:
        log.warning("Failed tickers: %s", ', '.join(errors[:10]))

    return len(all_data)

def run_continuous():
    """Run continuous fetch loop"""
    log.info("=" * 70)
    log.info("CONTINUOUS DATA FETCHER")
    log.info("=" * 70)
    log.info("Refresh interval: %d seconds", REFRESH_INTERVAL)
    log.info("Tickers per cycle: %d (of %d liquid options tickers)",
             MAX_TICKERS_PER_CYCLE, len(TOP_100_LIQUID_OPTIONS))
    log.info("Press Ctrl+C to stop")
    log.info("=" * 70)

    cycle_count = 0

    try:
        while True:
            cycle_count += 1
            log.info("CYCLE #%d", cycle_count)

            # Fetch data
            contract_count = fetch_all_tickers()

            # Wait for next cycle
            next_run = datetime.now().timestamp() + REFRESH_INTERVAL
            next_run_time = datetime.fromtimestamp(next_run).strftime('%H:%M:%S')

            log.info("Next fetch at: %s (waiting %ds)", next_run_time, REFRESH_INTERVAL)

            time.sleep(REFRESH_INTERVAL)

    except KeyboardInterrupt:
        log.info("Stopped by user after %d cycles", cycle_count)

if __name__ == "__main__":
    # Run once immediately, then start continuous loop
    log.info("Running initial fetch...")
    fetch_all_tickers()

    print("\n" + "="*70)
    input("Press Enter to start continuous fetching (Ctrl+C to stop)...")
    print()

    run_continuous()

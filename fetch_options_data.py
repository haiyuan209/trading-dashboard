"""
Options Data Fetcher with Retry Logic
=======================================
Fetches option chains from Schwab API with exponential backoff retry.
Supports parallel fetching for faster data refresh.
"""

import schwab
import json
import os
import csv
import time
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from logger import get_logger

log = get_logger("fetch_options_data")

# --- DNS MONKEY PATCH ---
# Fix for system-specific getaddrinfo failure on api.schwabapi.com
original_getaddrinfo = socket.getaddrinfo
def patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if host == 'api.schwabapi.com':
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('69.192.139.216', port))]
    return original_getaddrinfo(host, port, family, type, proto, flags)
socket.getaddrinfo = patched_getaddrinfo
# ------------------------

# Load environment variables
load_dotenv()

APP_KEY = os.getenv('SCHWAB_APP_KEY')
APP_SECRET = os.getenv('SCHWAB_APP_SECRET')
TOKEN_PATH = 'token.json'

# Import the curated list of most liquid options tickers
from ticker_list import TOP_100_LIQUID_OPTIONS

TARGET_TICKERS = TOP_100_LIQUID_OPTIONS  # Use top 100 liquid options tickers


def _get_retry_config():
    """Get retry configuration."""
    try:
        from config import load_config
        cfg = load_config()
        return cfg.fetcher.api_retry_attempts, cfg.fetcher.api_retry_delay
    except Exception:
        return 3, 2


def get_client():
    try:
        # Disable enum enforcement to allow string inputs like '$SPX' if needed
        return schwab.auth.client_from_token_file(TOKEN_PATH, APP_KEY, APP_SECRET, enforce_enums=False)
    except Exception as e:
        log.error("Error initializing client: %s", e)
        return None


def fetch_option_data(client, ticker):
    """Fetch option chain with exponential backoff retry.

    Handles index symbols ($SPX, $NDX, etc.) which may return
    multiple contracts per strike (e.g. SPX + SPXW).
    """
    max_attempts, base_delay = _get_retry_config()

    # Normalize display name (strip $ for storage, keep for API call)
    display_ticker = ticker.lstrip('$')

    for attempt in range(1, max_attempts + 1):
        try:
            log.info("Fetching option chain for %s (attempt %d/%d)...", ticker, attempt, max_attempts)

            resp = client.get_option_chain(
                ticker,
                contract_type=schwab.client.Client.Options.ContractType.ALL,
                strike_count=100,
                include_underlying_quote=True
            )

            if resp.status_code != 200:
                log.warning("  %s failed with status %d", ticker, resp.status_code)
                if attempt < max_attempts:
                    delay = base_delay * (2 ** (attempt - 1))
                    log.info("  Retrying in %ds...", delay)
                    time.sleep(delay)
                    continue
                return []

            data = resp.json()
            if data.get('status') != 'SUCCESS':
                log.warning("  %s API returned status: %s", ticker, data.get('status'))
                return []

            rows = []

            # Helper to process map
            def process_map(exp_map, option_type):
                if not exp_map: return
                for date_key, strikes in exp_map.items():
                    for strike_price, contracts in strikes.items():
                        # Schwab may return multiple contracts per strike
                        # (e.g. for $SPX: [SPX standard, SPXW weekly])
                        for contract in contracts:
                            # Trade Side Logic
                            bid = contract.get('bid', 0)
                            ask = contract.get('ask', 0)
                            last = contract.get('last', 0)

                            trade_side = 'MID'
                            if ask > 0 and bid > 0:
                                mid_price = (bid + ask) / 2
                                if last >= ask:
                                    trade_side = 'ASK (Buy)'
                                elif last <= bid:
                                    trade_side = 'BID (Sell)'
                                elif last > mid_price:
                                    trade_side = 'Near ASK'
                                elif last < mid_price:
                                    trade_side = 'Near BID'

                            row = {
                                'Symbol': display_ticker,
                                'Underlying': data.get('symbol', ticker),
                                'UnderlyingPrice': data.get('underlyingPrice', 0),
                                'OptionSymbol': contract.get('symbol'),
                                'Expiration': contract.get('expirationDate'),
                                'Strike': contract.get('strikePrice'),
                                'Type': option_type,
                                'Bid': bid,
                                'Ask': ask,
                                'Last': last,
                                'TradeSide': trade_side,
                                'Volume': contract.get('totalVolume'),
                                'OpenInterest': contract.get('openInterest'),
                                'Delta': contract.get('delta'),
                                'Gamma': contract.get('gamma'),
                                'Theta': contract.get('theta'),
                                'Vega': contract.get('vega'),
                                'Rho': contract.get('rho'),
                                'ImpliedVol': contract.get('volatility')
                            }
                            rows.append(row)

            process_map(data.get('callExpDateMap', {}), 'CALL')
            process_map(data.get('putExpDateMap', {}), 'PUT')

            log.info("  %s: Retrieved %d contracts", display_ticker, len(rows))
            return rows

        except Exception as e:
            log.error("  Exception fetching %s: %s", ticker, e)
            if attempt < max_attempts:
                delay = base_delay * (2 ** (attempt - 1))
                log.info("  Retrying in %ds...", delay)
                time.sleep(delay)
            else:
                log.error("  All %d attempts failed for %s", max_attempts, ticker)
                return []

    return []


def save_analytics_data(all_data):
    """Generate analytics data (all_tickers_data.js) from options data"""
    from datetime import datetime
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


def _fetch_one(client, ticker):
    """Fetch a single ticker — used as a ThreadPoolExecutor target."""
    try:
        contracts = fetch_option_data(client, ticker)
        return ticker, contracts or []
    except Exception as e:
        log.error("Unexpected error fetching %s: %s", ticker, e)
        return ticker, []


PARALLEL_WORKERS = 5  # concurrent API calls (5 = safe for 1GB RAM servers)


def main():
    client = get_client()
    if not client:
        return

    output_file = 'option_greeks_data.csv'
    fieldnames = [
        'Symbol', 'Underlying', 'UnderlyingPrice', 'OptionSymbol', 'Expiration', 'Strike', 'Type',
        'Bid', 'Ask', 'Last', 'TradeSide', 'Volume', 'OpenInterest',
        'Delta', 'Gamma', 'Theta', 'Vega', 'Rho', 'ImpliedVol'
    ]

    log.info("Starting parallel fetch for %d tickers (%d workers)...", len(TARGET_TICKERS), PARALLEL_WORKERS)
    start_time = time.time()

    all_contracts = []
    errors = []

    with ThreadPoolExecutor(max_workers=PARALLEL_WORKERS) as executor:
        futures = {}
        for i, ticker in enumerate(TARGET_TICKERS):
            # Small stagger to avoid burst rate limiting
            future = executor.submit(_fetch_one, client, ticker)
            futures[future] = ticker

        for future in as_completed(futures):
            ticker = futures[future]
            try:
                _, contracts = future.result()
                if contracts:
                    all_contracts.extend(contracts)
                else:
                    errors.append(ticker)
            except Exception as e:
                log.error("Future error for %s: %s", ticker, e)
                errors.append(ticker)

    elapsed = time.time() - start_time
    log.info("Fetched %d contracts from %d tickers in %.1fs (%d errors)",
             len(all_contracts), len(TARGET_TICKERS) - len(errors), elapsed, len(errors))

    # Save CSV
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_contracts)

    # Save JS file for dashboard
    log.info("Generating dashboard data file...")
    for row in all_contracts:
        for k, v in row.items():
            if k not in ['Symbol', 'Underlying', 'OptionSymbol', 'Expiration', 'Type', 'TradeSide']:
                try:
                    row[k] = float(v) if v else 0
                except:
                    pass

    with open('option_data.js', 'w', encoding='utf-8') as f:
        f.write(f"const OPTION_DATA = {json.dumps(all_contracts)};")

    # Also generate analytics data for analytics view
    save_analytics_data(all_contracts)

    log.info("Done! Data saved to %s and option_data.js", output_file)

if __name__ == "__main__":
    main()


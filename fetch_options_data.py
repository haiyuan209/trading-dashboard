import schwab
import json
import os
import csv
import time
import socket
from dotenv import load_dotenv

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

def get_client():
    try:
        # Disable enum enforcement to allow string inputs like '$SPX' if needed
        return schwab.auth.client_from_token_file(TOKEN_PATH, APP_KEY, APP_SECRET, enforce_enums=False)
    except Exception as e:
        print(f"Error initializing client: {e}")
        return None

def fetch_option_data(client, ticker):
    print(f"Fetching option chain for {ticker}...")
    try:
        # Get a wide range of strikes which will naturally include multiple expirations
        # strike_count=100 ensures we get many strikes above and below ATM
        # This will fetch all available expirations for all those strikes
        resp = client.get_option_chain(
            ticker,
            contract_type=schwab.client.Client.Options.ContractType.ALL,
            strike_count=100,
            include_underlying_quote=True
        )
        
        if resp.status_code != 200:
            print(f"  Failed. Status: {resp.status_code}")
            return []

        data = resp.json()
        if data.get('status') != 'SUCCESS':
            print(f"  API returned status: {data.get('status')}")
            return []

        rows = []
        
        # Helper to process map
        def process_map(exp_map, option_type):
            if not exp_map: return
            for date_key, strikes in exp_map.items():
                for strike_price, contracts in strikes.items():
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
                            'Symbol': ticker,
                            'Underlying': data.get('symbol', ticker),
                            'UnderlyingPrice': data.get('underlyingPrice', 0),
                            'OptionSymbol': contract.get('symbol'),
                            'Expiration': contract.get('expirationDate'),
                            'Strike': contract.get('strikePrice'),
                            'Type': option_type,
                            'Bid': bid,
                            'Ask': ask,
                            'Last': last,
                            'TradeSide': trade_side, # Enriched Data
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
        
        print(f"  Retrieved {len(rows)} contracts.")
        return rows

    except Exception as e:
        print(f"  Exception fetching {ticker}: {e}")
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
    
    print(f"[OK] Saved {len(ticker_data)} tickers to all_tickers_data.js")


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

    print(f"Starting fetch for {len(TARGET_TICKERS)} tickers...")
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for ticker in TARGET_TICKERS:
            contracts = fetch_option_data(client, ticker)
            if contracts:
                writer.writerows(contracts)
            
            # Rate limit politeness
            time.sleep(0.5)

    # ---------------------------------------------------------
    # NEW: Also save as a JS file for the Dashboard (Bypasses CORS)
    # ---------------------------------------------------------
    print("Generating dashboard data file...")
    # We need to re-read or persist the rows. 
    # Since we streamed them to CSV, let's just re-read the CSV to be efficient 
    # or just collect them in memory if memory permits (3MB is fine).
    
    # Let's collect in memory for simplicity in this run, but we only wrote to disk.
    # Re-reading is safer to match CSV exactly.
    all_rows = []
    with open(output_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert numeric types back from string
            for k, v in row.items():
                if k not in ['Symbol', 'Underlying', 'OptionSymbol', 'Expiration', 'Type', 'TradeSide']:
                    try:
                        row[k] = float(v) if v else 0
                    except:
                        pass
            all_rows.append(row)
            
    with open('option_data.js', 'w', encoding='utf-8') as f:
        f.write(f"const OPTION_DATA = {json.dumps(all_rows)};")
    
    # Also generate analytics data for analytics view
    save_analytics_data(all_rows)
        
    print(f"Done! Data saved to {output_file} and option_data.js")

if __name__ == "__main__":
    main()

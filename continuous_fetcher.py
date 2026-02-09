"""
Continuous Data Fetcher - Runs every 5 minutes
Fetches options data for all tickers and updates dashboard files
"""

import time
import json
from datetime import datetime
from ticker_list import TOP_100_LIQUID_OPTIONS
from fetch_options_data import get_client, fetch_option_data
import os

REFRESH_INTERVAL = 60  # 1 minute in seconds
MAX_TICKERS_PER_CYCLE = 100  # Limit to avoid rate limiting

def save_option_data(all_data):
    """Save options data to JavaScript file for dashboard"""
    timestamp = datetime.now().isoformat()
    
    # Generate JavaScript file
    js_content = f"// Auto-generated at {timestamp}\nconst OPTION_DATA = {json.dumps(all_data, indent=2)};\n"
    
    with open('option_data.js', 'w', encoding='utf-8') as f:
        f.write(js_content)
    
    print(f"[OK] Saved {len(all_data)} contracts to option_data.js")

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
    
    print(f"[OK] Saved {len(ticker_data)} tickers to all_tickers_data.js")

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
    
    print(f"[OK] Updated metadata")

def fetch_all_tickers():
    """Fetch data for all tickers"""
    print("=" * 70)
    print(f"Data Fetch Cycle Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    client = get_client()
    if not client:
        print("ERROR: Could not initialize Schwab client")
        return
    
    all_data = []
    errors = []
    
    # Limit tickers to avoid overwhelming API
    tickers_to_fetch = TOP_100_LIQUID_OPTIONS[:MAX_TICKERS_PER_CYCLE]
    total_tickers = len(tickers_to_fetch)
    
    for i, ticker in enumerate(tickers_to_fetch, 1):
        print(f"\n[{i}/{total_tickers}] Fetching {ticker}...")
        
        try:
            ticker_data = fetch_option_data(client, ticker)
            if ticker_data:
                all_data.extend(ticker_data)
                print(f"  [OK] Got {len(ticker_data)} contracts")
            else:
                print(f"  [!] No data returned")
                errors.append(ticker)
            
            # Small delay to avoid rate limiting
            time.sleep(0.5)
            
        except Exception as e:
            print(f"  [X] Error: {e}")
            errors.append(ticker)
    
    # Save data
    print("\n" + "=" * 70)
    print("Saving data...")
    print("=" * 70)
    
    save_option_data(all_data)  # For heatmap view
    save_analytics_data(all_data)  # For analytics view
    save_metadata(len(tickers_to_fetch), len(all_data), errors)
    
    print(f"\n[OK] Fetch cycle complete")
    print(f"  Total contracts: {len(all_data)}")
    print(f"  Errors: {len(errors)}")
    if errors:
        print(f"  Failed tickers: {', '.join(errors[:10])}")
    
    return len(all_data)

def run_continuous():
    """Run continuous fetch loop"""
    print("=" * 70)
    print("CONTINUOUS DATA FETCHER")
    print("=" * 70)
    print(f"Refresh interval: {REFRESH_INTERVAL} seconds ({REFRESH_INTERVAL//60} minutes)")
    print(f"Tickers per cycle: {MAX_TICKERS_PER_CYCLE} (of {len(TOP_100_LIQUID_OPTIONS)} liquid options tickers)")
    print("Press Ctrl+C to stop")
    print("=" * 70)
    
    cycle_count = 0
    
    try:
        while True:
            cycle_count += 1
            print(f"\n\n{'='*70}")
            print(f"CYCLE #{cycle_count}")
            print(f"{'='*70}")
            
            # Fetch data
            contract_count = fetch_all_tickers()
            
            # Wait for next cycle
            next_run = datetime.now().timestamp() + REFRESH_INTERVAL
            next_run_time = datetime.fromtimestamp(next_run).strftime('%H:%M:%S')
            
            print(f"\n⏰ Next fetch at: {next_run_time}")
            print(f"Waiting {REFRESH_INTERVAL} seconds...")
            
            time.sleep(REFRESH_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n\n" + "="*70)
        print("Stopped by user")
        print(f"Total cycles completed: {cycle_count}")
        print("="*70)

if __name__ == "__main__":
    # Run once immediately, then start continuous loop
    print("Running initial fetch...")
    fetch_all_tickers()
    
    print("\n" + "="*70)
    input("Press Enter to start continuous fetching (Ctrl+C to stop)...")
    print()
    
    run_continuous()

"""
Test E-mini Futures Options Fetching
Tests if Schwab API can retrieve options data for /ES and /NQ futures
"""

import sys
from fetch_options_data import get_client, fetch_option_data

def test_futures_options():
    """Test fetching E-mini futures options"""
    
    # E-mini futures symbols to test
    futures_symbols = [
        '/ES',   # S&P 500 E-mini
        '/NQ',   # Nasdaq-100 E-mini
        'ES',    # Try without slash
        'NQ',    # Try without slash
    ]
    
    print("=" * 60)
    print("TESTING E-MINI FUTURES OPTIONS ACCESS")
    print("=" * 60)
    
    try:
        client = get_client()
        print("[OK] Successfully connected to Schwab API\n")
    except Exception as e:
        print(f"[FAIL] Failed to connect to Schwab API: {e}")
        return
    
    results = {}
    
    for symbol in futures_symbols:
        print(f"\n{'='*60}")
        print(f"Testing symbol: {symbol}")
        print(f"{'='*60}")
        
        try:
            # Attempt to fetch options data
            data = fetch_option_data(client, symbol)
            
            if data and len(data) > 0:
                print(f"[SUCCESS] Retrieved {len(data)} option contracts for {symbol}")
                print(f"  Sample contract: {data[0]['Symbol']} {data[0]['Strike']}")
                print(f"  Underlying price: ${data[0]['UnderlyingPrice']:.2f}")
                results[symbol] = {
                    'success': True,
                    'count': len(data),
                    'sample': data[0]
                }
            else:
                print(f"[FAIL] No data returned for {symbol}")
                results[symbol] = {'success': False, 'error': 'No data returned'}
                
        except Exception as e:
            print(f"[ERROR] Error fetching {symbol}: {str(e)}")
            results[symbol] = {'success': False, 'error': str(e)}
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}\n")
    
    successful = [sym for sym, res in results.items() if res.get('success')]
    failed = [sym for sym, res in results.items() if not res.get('success')]
    
    if successful:
        print(f"[OK] Successful symbols ({len(successful)}):")
        for sym in successful:
            print(f"  - {sym}: {results[sym]['count']} contracts")
    
    if failed:
        print(f"\n[FAIL] Failed symbols ({len(failed)}):")
        for sym in failed:
            print(f"  - {sym}: {results[sym].get('error', 'Unknown error')}")
    
    # Recommendation
    print(f"\n{'='*60}")
    print("RECOMMENDATION")
    print(f"{'='*60}\n")
    
    if successful:
        print(f"[OK] E-mini futures options ARE AVAILABLE via Schwab API!")
        print(f"[OK] Use these symbols: {', '.join(successful)}")
        print(f"[OK] Ready to add to unified dashboard")
    else:
        print(f"[FAIL] E-mini futures options are NOT accessible")
        print(f"  Possible reasons:")
        print(f"  - Account doesn't have futures trading approval")
        print(f"  - API doesn't support futures options")
        print(f"  - Different symbol format required")
    
    return results

if __name__ == "__main__":
    test_futures_options()

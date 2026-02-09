"""
Test Additional Futures Symbol Formats
The Schwab API may use different symbol formats for futures
"""

from fetch_options_data import get_client, fetch_option_data

def test_additional_formats():
    """Test various futures symbol formats"""
    
    # Try different symbol formats that brokers might use
    test_symbols = [
        # E-mini S&P 500
        '$ES',
        'ES.FUT',
        'ESH24',  # March 2024 contract
        'ESM24',  # June 2024 contract
        '@ES',
        'ES-FUT',
        
        # E-mini Nasdaq
        '$NQ',
        'NQ.FUT',
        'NQH24',
        'NQM24',
        '@NQ',
        'NQ-FUT',
    ]
    
    print("=" * 60)
    print("TESTING ALTERNATIVE FUTURES SYMBOL FORMATS")
    print("=" * 60)
    
    client = get_client()
    
    for symbol in test_symbols:
        print(f"\nTesting: {symbol}")
        try:
            data = fetch_option_data(client, symbol)
            if data and len(data) > 0:
                price = data[0]['UnderlyingPrice']
                print(f"  [SUCCESS] {len(data)} contracts, Price: ${price:.2f}")
                
                # E-mini S&P 500 should be around $5000-6000
                # E-mini Nasdaq should be around $18000-20000
                if price > 4000:
                    print(f"  ** This might be an E-mini! Price in expected range **")
            else:
                print(f"  [FAIL] No data")
        except Exception as e:
            print(f"  [ERROR] {str(e)[:50]}")

if __name__ == "__main__":
    test_additional_formats()

"""
Initial OAuth Authentication for Schwab API
This script performs the initial OAuth login flow to create token.json
"""
import os
import sys
import socket
from dotenv import load_dotenv
import schwab

# DNS monkey patch
original_getaddrinfo = socket.getaddrinfo
def patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if host == 'api.schwabapi.com':
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('69.192.139.216', port))]
    return original_getaddrinfo(host, port, family, type, proto, flags)
socket.getaddrinfo = patched_getaddrinfo

# Clear proxy settings
if 'HTTP_PROXY' in os.environ:
    del os.environ['HTTP_PROXY']
if 'HTTPS_PROXY' in os.environ:
    del os.environ['HTTPS_PROXY']

load_dotenv()

APP_KEY = os.getenv('SCHWAB_APP_KEY')
APP_SECRET = os.getenv('SCHWAB_APP_SECRET')
CALLBACK_URL = os.getenv('SCHWAB_CALLBACK_URL')
TOKEN_PATH = 'token.json'

def main():
    print("=" * 70)
    print("Schwab API - Initial OAuth Authentication")
    print("=" * 70)
    
    if not all([APP_KEY, APP_SECRET, CALLBACK_URL]):
        print("\n[ERROR] Missing credentials in .env file")
        print("Please ensure SCHWAB_APP_KEY, SCHWAB_APP_SECRET, and SCHWAB_CALLBACK_URL are set")
        return
    
    print(f"\n[INFO] Using App Key: {APP_KEY[:10]}...")
    print(f"[INFO] Using Callback URL: {CALLBACK_URL}")
    print(f"[INFO] Token will be saved to: {os.path.abspath(TOKEN_PATH)}")
    
    # Check if token already exists
    if os.path.exists(TOKEN_PATH):
        print(f"\n[WARNING] Existing token found at {TOKEN_PATH}")
        response = input("Delete existing token and create new one? (yes/no): ")
        if response.lower() != 'yes':
            print("Aborted.")
            return
        os.remove(TOKEN_PATH)
        print("[OK] Deleted existing token")
    
    try:
        print("\n" + "=" * 70)
        print("STARTING OAUTH FLOW")
        print("=" * 70)
        print("\nA browser window will open for you to:")
        print("  1. Log in to your Schwab account")
        print("  2. Authorize this application")
        print("  3. You'll be redirected to the callback URL")
        print("  4. Copy the ENTIRE URL from your browser address bar")
        print("  5. Paste it back here when prompted")
        print("\n" + "=" * 70)
        
        input("\nPress ENTER when ready to begin...")
        
        # Perform interactive OAuth flow
        client = schwab.auth.client_from_manual_flow(
            APP_KEY,
            APP_SECRET,
            CALLBACK_URL,
            TOKEN_PATH
        )
        
        print("\n" + "=" * 70)
        print("[SUCCESS] OAuth authentication completed!")
        print("=" * 70)
        print(f"\n[OK] Token saved to: {os.path.abspath(TOKEN_PATH)}")
        
        # Test the connection
        print("\n[INFO] Testing API connection...")
        resp = client.get_quote('SPY')
        if resp.status_code == 200:
            print("[SUCCESS] API connection verified! SPY quote retrieved successfully.")
            data = resp.json()
            spy_price = data.get('SPY', {}).get('quote', {}).get('lastPrice', 'N/A')
            print(f"[INFO] SPY Price: ${spy_price}")
        else:
            print(f"[WARNING] API test returned status {resp.status_code}")
            print(f"Response: {resp.text[:200]}")
        
        print("\n" + "=" * 70)
        print("SETUP COMPLETE!")
        print("=" * 70)
        print("\nYou can now run:")
        print("  python fetch_options_data.py")
        print("\n")
        
    except Exception as e:
        print(f"\n[ERROR] OAuth flow failed: {e}")
        import traceback
        traceback.print_exc()
        return

if __name__ == "__main__":
    main()

"""
Schwab API Token Refresh Script
================================
This script refreshes the Schwab API token to prevent expiration.
Run this daily via Windows Task Scheduler to keep the token alive.

The schwab-py library automatically handles token refresh when you
create a client from the token file.
"""

import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv
import socket

# --- DNS MONKEY PATCH ---
# Fix for system-specific getaddrinfo failure on api.schwabapi.com
original_getaddrinfo = socket.getaddrinfo
def patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if host == 'api.schwabapi.com':
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('69.192.139.216', port))]
    return original_getaddrinfo(host, port, family, type, proto, flags)
socket.getaddrinfo = patched_getaddrinfo
# ------------------------

import schwab

# Load environment variables
load_dotenv()

APP_KEY = os.getenv('SCHWAB_APP_KEY')
APP_SECRET = os.getenv('SCHWAB_APP_SECRET')
TOKEN_PATH = 'token.json'

# Log file path
LOG_FILE = 'token_refresh.log'

def log_message(message):
    """Write message to log file with timestamp"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] {message}\n"
    
    # Print to console
    print(log_entry.strip())
    
    # Append to log file
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Warning: Could not write to log file: {e}")

def get_token_info():
    """Read and display token information"""
    try:
        with open(TOKEN_PATH, 'r') as f:
            token_data = json.load(f)
        
        creation_time = datetime.fromtimestamp(token_data.get('creation_timestamp', 0))
        expires_in = token_data.get('token', {}).get('expires_in', 0)
        
        return {
            'created': creation_time,
            'expires_in_seconds': expires_in,
            'expires_in_minutes': expires_in / 60
        }
    except Exception as e:
        return None

def refresh_token():
    """Refresh the Schwab API token"""
    log_message("=" * 60)
    log_message("Starting Token Refresh")
    
    # Check if credentials exist
    if not all([APP_KEY, APP_SECRET]):
        log_message("ERROR: Missing credentials in .env file")
        return False
    
    # Check if token file exists
    if not os.path.exists(TOKEN_PATH):
        log_message(f"ERROR: Token file not found at {TOKEN_PATH}")
        log_message("Please run client.py to authenticate first")
        return False
    
    # Get token info before refresh
    before_info = get_token_info()
    if before_info:
        log_message(f"Token created: {before_info['created']}")
        log_message(f"Access token expires in: {before_info['expires_in_minutes']:.1f} minutes")
    
    try:
        # Create client - this automatically refreshes the token if needed
        log_message("Connecting to Schwab API...")
        client = schwab.auth.client_from_token_file(
            TOKEN_PATH,
            APP_KEY,
            APP_SECRET,
            enforce_enums=False
        )
        
        # Make a simple API call to verify the token works
        log_message("Verifying token with test API call...")
        resp = client.get_quote('SPY')
        
        if resp.status_code == 200:
            log_message("✓ Token refresh successful!")
            log_message("✓ API connection verified (SPY quote fetched)")
            
            # Get token info after refresh
            after_info = get_token_info()
            if after_info:
                log_message(f"New access token expires in: {after_info['expires_in_minutes']:.1f} minutes")
            
            return True
        else:
            log_message(f"WARNING: API call returned status {resp.status_code}")
            log_message(f"Response: {resp.text[:200]}")
            return False
            
    except Exception as e:
        log_message(f"ERROR: Token refresh failed - {str(e)}")
        import traceback
        log_message(traceback.format_exc())
        return False
    finally:
        log_message("=" * 60)
        log_message("")  # Empty line for readability

if __name__ == "__main__":
    success = refresh_token()
    sys.exit(0 if success else 1)

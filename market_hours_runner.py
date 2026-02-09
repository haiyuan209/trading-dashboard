"""
Market Hours Runner for Continuous Fetcher
Runs continuous_fetcher.py only during market hours (9:30 AM - 4:00 PM ET, Mon-Fri)
"""

import time
import sys
from datetime import datetime, time as dt_time
import pytz
from continuous_fetcher import fetch_all_tickers

# Market hours (Eastern Time)
MARKET_OPEN = dt_time(9, 30)   # 9:30 AM ET
MARKET_CLOSE = dt_time(16, 0)  # 4:00 PM ET
REFRESH_INTERVAL = 60  # 1 minute

def is_market_hours():
    """Check if current time is during market hours"""
    et = pytz.timezone('America/New_York')
    now_et = datetime.now(et)
    
    # Check if weekday (0=Monday, 6=Sunday)
    if now_et.weekday() >= 5:  # Saturday or Sunday
        return False
    
    # Check if within market hours
    current_time = now_et.time()
    return MARKET_OPEN <= current_time <= MARKET_CLOSE

def wait_for_market_open():
    """Wait until market opens"""
    et = pytz.timezone('America/New_York')
    
    while not is_market_hours():
        now_et = datetime.now(et)
        current_time = now_et.time()
        
        if now_et.weekday() >= 5:
            # Weekend - wait until Monday
            print(f"[{now_et.strftime('%Y-%m-%d %H:%M:%S %Z')}] Weekend - Market closed")
            time.sleep(3600)  # Check every hour
        elif current_time < MARKET_OPEN:
            # Before market open
            minutes_until_open = ((datetime.combine(now_et.date(), MARKET_OPEN) - 
                                  datetime.combine(now_et.date(), current_time)).seconds // 60)
            print(f"[{now_et.strftime('%Y-%m-%d %H:%M:%S %Z')}] Market opens in {minutes_until_open} minutes")
            time.sleep(60)  # Check every minute
        else:
            # After market close
            print(f"[{now_et.strftime('%Y-%m-%d %H:%M:%S %Z')}] Market closed for today")
            time.sleep(3600)  # Check every hour

def run_during_market_hours():
    """Run continuous fetcher only during market hours"""
    et = pytz.timezone('America/New_York')
    
    print("="*70)
    print("CONTINUOUS FETCHER - MARKET HOURS MODE")
    print("="*70)
    print(f"Market Hours: {MARKET_OPEN.strftime('%I:%M %p')} - {MARKET_CLOSE.strftime('%I:%M %p')} ET")
    print(f"Refresh Interval: {REFRESH_INTERVAL} seconds")
    print("="*70)
    print()
    
    try:
        while True:
            if is_market_hours():
                now_et = datetime.now(et)
                print(f"\\n[{now_et.strftime('%Y-%m-%d %H:%M:%S %Z')}] Market is OPEN - Fetching data...")
                
                try:
                    fetch_all_tickers()
                    print(f"[OK] Data updated successfully")
                except Exception as e:
                    print(f"[ERROR] Fetch failed: {e}")
                
                # Wait for next interval
                time.sleep(REFRESH_INTERVAL)
            else:
                now_et = datetime.now(et)
                print(f"\\n[{now_et.strftime('%Y-%m-%d %H:%M:%S %Z')}] Market is CLOSED")
                wait_for_market_open()
                
    except KeyboardInterrupt:
        print("\\n\\nStopped by user")
        sys.exit(0)

if __name__ == "__main__":
    run_during_market_hours()

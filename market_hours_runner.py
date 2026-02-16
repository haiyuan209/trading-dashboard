"""
Market Hours Runner for Continuous Fetcher
Runs continuous_fetcher.py only during market hours (configurable via config.yaml)
"""

import time
import sys
from datetime import datetime, time as dt_time
import pytz
from continuous_fetcher import fetch_all_tickers
from config import load_config
from logger import get_logger

log = get_logger("market_hours_runner")
cfg = load_config()

# Parse market hours from config
_open_parts = cfg.market_hours.open.split(":")
_close_parts = cfg.market_hours.close.split(":")
MARKET_OPEN = dt_time(int(_open_parts[0]), int(_open_parts[1]))
MARKET_CLOSE = dt_time(int(_close_parts[0]), int(_close_parts[1]))
REFRESH_INTERVAL = cfg.fetcher.refresh_interval
TIMEZONE = cfg.market_hours.timezone

def is_market_hours():
    """Check if current time is during market hours"""
    et = pytz.timezone(TIMEZONE)
    now_et = datetime.now(et)

    # Check if weekday (0=Monday, 6=Sunday)
    if now_et.weekday() >= 5:  # Saturday or Sunday
        return False

    # Check if within market hours
    current_time = now_et.time()
    return MARKET_OPEN <= current_time <= MARKET_CLOSE

def wait_for_market_open():
    """Wait until market opens"""
    et = pytz.timezone(TIMEZONE)

    while not is_market_hours():
        now_et = datetime.now(et)
        current_time = now_et.time()

        if now_et.weekday() >= 5:
            # Weekend - wait until Monday
            log.info("[%s] Weekend - Market closed", now_et.strftime('%Y-%m-%d %H:%M:%S %Z'))
            time.sleep(3600)  # Check every hour
        elif current_time < MARKET_OPEN:
            # Before market open
            minutes_until_open = ((datetime.combine(now_et.date(), MARKET_OPEN) -
                                  datetime.combine(now_et.date(), current_time)).seconds // 60)
            log.info("[%s] Market opens in %d minutes",
                     now_et.strftime('%Y-%m-%d %H:%M:%S %Z'), minutes_until_open)
            time.sleep(60)  # Check every minute
        else:
            # After market close
            log.info("[%s] Market closed for today", now_et.strftime('%Y-%m-%d %H:%M:%S %Z'))
            time.sleep(3600)  # Check every hour

def run_during_market_hours():
    """Run continuous fetcher only during market hours"""
    et = pytz.timezone(TIMEZONE)

    log.info("=" * 70)
    log.info("CONTINUOUS FETCHER - MARKET HOURS MODE")
    log.info("=" * 70)
    log.info("Market Hours: %s - %s %s",
             MARKET_OPEN.strftime('%I:%M %p'), MARKET_CLOSE.strftime('%I:%M %p'), TIMEZONE)
    log.info("Refresh Interval: %d seconds", REFRESH_INTERVAL)
    log.info("=" * 70)

    try:
        while True:
            if is_market_hours():
                now_et = datetime.now(et)
                log.info("[%s] Market is OPEN - Fetching data...",
                         now_et.strftime('%Y-%m-%d %H:%M:%S %Z'))

                try:
                    fetch_all_tickers()
                    log.info("Data updated successfully")
                except Exception as e:
                    log.error("Fetch failed: %s", e)

                # Wait for next interval
                time.sleep(REFRESH_INTERVAL)
            else:
                now_et = datetime.now(et)
                log.info("[%s] Market is CLOSED", now_et.strftime('%Y-%m-%d %H:%M:%S %Z'))
                wait_for_market_open()

    except KeyboardInterrupt:
        log.info("Stopped by user")
        sys.exit(0)

if __name__ == "__main__":
    run_during_market_hours()

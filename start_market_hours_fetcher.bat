@echo off
echo ======================================================================
echo MARKET HOURS DATA FETCHER
echo ======================================================================
echo.
echo This will automatically fetch options data during market hours
echo (9:30 AM - 4:00 PM ET, Monday-Friday)
echo.
echo Press Ctrl+C to stop
echo ======================================================================
echo.

cd /d "%~dp0"
python market_hours_runner.py
pause

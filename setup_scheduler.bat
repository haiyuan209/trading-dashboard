@echo off
REM Setup Windows Task Scheduler for Schwab Token Refresh
REM This batch file creates a scheduled task that runs daily at 9:00 AM

echo ============================================
echo Schwab Token Auto-Refresh Setup
echo ============================================
echo.

REM Get the current directory
set SCRIPT_DIR=%~dp0
set PYTHON_SCRIPT=%SCRIPT_DIR%refresh_token.py

REM Check if Python script exists
if not exist "%PYTHON_SCRIPT%" (
    echo ERROR: refresh_token.py not found!
    echo Please make sure refresh_token.py is in the same directory.
    pause
    exit /b 1
)

REM Find Python executable
for /f "delims=" %%i in ('where python') do set PYTHON_EXE=%%i

if not defined PYTHON_EXE (
    echo ERROR: Python not found in PATH!
    echo Please install Python or add it to your PATH.
    pause
    exit /b 1
)

echo Python found: %PYTHON_EXE%
echo Script: %PYTHON_SCRIPT%
echo.

REM Remove existing task if it exists
schtasks /Query /TN "SchwabTokenRefresh" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Removing existing scheduled task...
    schtasks /Delete /TN "SchwabTokenRefresh" /F
    echo.
)

REM Create the scheduled task
echo Creating scheduled task...
schtasks /Create /TN "SchwabTokenRefresh" /TR "\"%PYTHON_EXE%\" \"%PYTHON_SCRIPT%\"" /SC DAILY /ST 09:00 /RL HIGHEST /F

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================
    echo SUCCESS! Scheduled task created.
    echo ============================================
    echo.
    echo Task Name: SchwabTokenRefresh
    echo Schedule: Daily at 9:00 AM
    echo Action: Run refresh_token.py
    echo.
    echo The token will be automatically refreshed every day.
    echo You can view/manage the task in Task Scheduler.
    echo.
    echo To test the refresh now, run:
    echo   python refresh_token.py
    echo.
) else (
    echo.
    echo ERROR: Failed to create scheduled task!
    echo Please run this batch file as Administrator.
    echo.
)

pause

# Schwab API Token Auto-Refresh Setup Guide

## 📋 Overview
This setup prevents your Schwab API token from expiring (which happens every 7 days without use) by automatically refreshing it daily.

## ✅ Files Created

### 1. `refresh_token.py`
- **Purpose**: Refreshes the Schwab API token
- **What it does**: Connects to Schwab API, auto-refreshes the token, and logs the result
- **Log file**: Creates `token_refresh.log` with timestamps

### 2. `setup_scheduler.bat` (Recommended)
- **Purpose**: Easy one-click setup for Windows Task Scheduler
- **Requires**: Administrator privileges

### 3. `setup_scheduler.ps1` (Alternative)
- **Purpose**: PowerShell version of the setup script
- **Requires**: PowerShell with elevated privileges

---

## 🚀 Quick Setup (2 Steps)

### Step 1: Test the Refresh Script
Run this command to verify everything works:
```bash
python refresh_token.py
```

**Expected output:**
```
[2026-01-23 XX:XX:XX] ============================================================
[2026-01-23 XX:XX:XX] Starting Token Refresh
[2026-01-23 XX:XX:XX] Token created: 2026-01-XX XX:XX:XX
[2026-01-23 XX:XX:XX] Access token expires in: XX.X minutes
[2026-01-23 XX:XX:XX] Connecting to Schwab API...
[2026-01-23 XX:XX:XX] Verifying token with test API call...
[2026-01-23 XX:XX:XX] ✓ Token refresh successful!
[2026-01-23 XX:XX:XX] ✓ API connection verified (SPY quote fetched)
```

> ⚠️ **Note**: If you get a 401 error, your token has expired. Run `python client.py` to reauthenticate first.

### Step 2: Set Up Scheduled Task

**Option A: Using Batch File (Easiest)**
1. Right-click on `setup_scheduler.bat`
2. Select **"Run as administrator"**
3. The task will be created automatically

**Option B: Manual Setup via Task Scheduler**
1. Open Task Scheduler (search "Task Scheduler" in Windows)
2. Click **"Create Basic Task"**
3. Fill in:
   - **Name**: `SchwabTokenRefresh`
   - **Description**: `Automatically refresh Schwab API token daily`
   - **Trigger**: Daily at 9:00 AM
   - **Action**: Start a program
   - **Program**: `python` (or full path: `C:\Users\blues\AppData\Local\Programs\Python\Python39\python.exe`)
   - **Arguments**: `"C:\Users\blues\Desktop\Trading Project\refresh_token.py"`
   - **Start in**: `C:\Users\blues\Desktop\Trading Project`
4. Check **"Run with highest privileges"**
5. Click **Finish**

---

## 📊 Verification

### Check if Task is Running
```powershell
schtasks /Query /TN "SchwabTokenRefresh"
```

### View Refresh Logs
Open `token_refresh.log` in the project directory to see all refresh attempts.

### Manual Token Refresh Anytime
```bash
python refresh_token.py
```

---

## 🔧 Customization

### Change Refresh Time
Edit the scheduled task time in Task Scheduler or modify line 23 in `setup_scheduler.bat`:
```batch
REM Change from 09:00 to your preferred time (24-hour format)
/ST 09:00
```

### Change Log File Location
Edit line 21 in `refresh_token.py`:
```python
LOG_FILE = 'token_refresh.log'  # Change to your preferred path
```

---

## ❓ Troubleshooting

### "Access is denied" when creating scheduled task
- **Solution**: Right-click and select "Run as administrator"

### "Token file not found" error
- **Solution**: Run `python client.py` first to create the initial token

### 401 Unauthorized error
- **Cause**: Your refresh token has expired (happens after 7 days of no API use)
- **Solution**: Run `python client.py` to reauthenticate

### Task not running automatically
1. Open Task Scheduler
2. Find "SchwabTokenRefresh" task
3. Right-click → "Run" to test manually
4. Check the "Last Run Result" column (should be 0x0 for success)

---

## 📝 How It Works

1. **Token Lifespan**:
   - Access Token: 30 minutes
   - Refresh Token: 7 days

2. **Auto-Refresh Process**:
   - The `schwab-py` library automatically uses the refresh token to get a new access token
   - As long as the refresh token is valid (less than 7 days old), you never need to manually reauthenticate
   - Running the script daily keeps the refresh token "alive" by continuously renewing it

3. **What the Scheduled Task Does**:
   - Runs `refresh_token.py` every day at 9:00 AM
   - The script connects to Schwab API
   - Makes a test API call (fetches SPY quote)
   - Automatically refreshes both access and refresh tokens
   - Logs the result to `token_refresh.log`

---

## ✨ Benefits

✅ **Never manually reauthenticate again**  
✅ **Fully automated** - runs in the background  
✅ **Detailed logging** - track all refresh attempts  
✅ **Error alerts** - check logs if something fails  
✅ **Lightweight** - runs in seconds  

---

## 🎯 Summary

Once set up, your token will automatically refresh every day at 9:00 AM, preventing the 7-day expiration. You'll never need to manually reauthenticate unless:
- You delete `token.json`
- The script fails to run for 7+ days consecutively
- You change your API credentials

**Next Steps**: Run `setup_scheduler.bat` as administrator to complete the setup!

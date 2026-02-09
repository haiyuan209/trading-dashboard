# Setup Windows Task Scheduler for Continuous Market Data Fetcher
# This script creates a scheduled task that starts at system boot and runs during market hours

$TaskName = "OptionsDataFetcher"
$ScriptPath = Join-Path $PSScriptRoot "market_hours_runner.py"
$PythonPath = (Get-Command python).Source
$LogPath = Join-Path $PSScriptRoot "fetcher.log"

# Check if script exists
if (-not (Test-Path $ScriptPath)) {
    Write-Host "ERROR: Script not found at $ScriptPath" -ForegroundColor Red
    exit 1
}

Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host "MARKET HOURS FETCHER - TASK SCHEDULER SETUP" -ForegroundColor Cyan
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host ""
Write-Host "Task Name: $TaskName" -ForegroundColor White
Write-Host "Script: $ScriptPath" -ForegroundColor Gray
Write-Host "Python: $PythonPath" -ForegroundColor Gray
Write-Host "Market Hours: 9:30 AM - 4:00 PM ET (Mon-Fri)" -ForegroundColor Yellow
Write-Host ""

# Define the action (run Python script)
$Action = New-ScheduledTaskAction -Execute $PythonPath -Argument "`"$ScriptPath`"" -WorkingDirectory $PSScriptRoot

# Define multiple triggers
$TriggerStartup = New-ScheduledTaskTrigger -AtStartup
$TriggerDaily = New-ScheduledTaskTrigger -Daily -At 9:00AM

# Define settings
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RunOnlyIfNetworkAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 12) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

# Get current user
$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -RunLevel Highest

# Remove existing task if it exists
$ExistingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($ExistingTask) {
    Write-Host "Removing existing task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Register the scheduled task
try {
    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $TriggerStartup, $TriggerDaily -Settings $Settings -Principal $Principal -Description "Automatically fetches options data during market hours (9:30 AM - 4:00 PM ET, Mon-Fri)"
    
    Write-Host ""
    Write-Host "[OK] Scheduled task created successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Task Details:" -ForegroundColor Cyan
    Write-Host "  - Starts automatically on system boot" -ForegroundColor White
    Write-Host "  - Also starts daily at 9:00 AM (backup trigger)" -ForegroundColor White
    Write-Host "  - Runs ONLY during market hours (9:30 AM - 4:00 PM ET)" -ForegroundColor Yellow
    Write-Host "  - Fetches data every 60 seconds" -ForegroundColor White
    Write-Host "  - Logs to: $LogPath" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Management Commands:" -ForegroundColor Cyan
    Write-Host "  Start:  Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Yellow
    Write-Host "  Stop:   Stop-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Yellow
    Write-Host "  Status: Get-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Yellow
    Write-Host ""
    
    # Ask if user wants to start it now
    $StartNow = Read-Host "Would you like to start the task now? (Y/N)"
    if ($StartNow -eq "Y" -or $StartNow -eq "y") {
        Write-Host ""
        Write-Host "Starting task..." -ForegroundColor Cyan
        Start-ScheduledTask -TaskName $TaskName
        Write-Host "[OK] Task started!" -ForegroundColor Green
        Write-Host ""
        Write-Host "To check if it's running:" -ForegroundColor Gray
        Write-Host "  Get-Process python" -ForegroundColor Yellow
    }
    
}
catch {
    Write-Host ""
    Write-Host "ERROR: Failed to create scheduled task" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}


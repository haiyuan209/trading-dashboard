# Setup Windows Task Scheduler for Schwab Token Refresh
# This script creates a scheduled task that runs daily at 9:00 AM

$TaskName = "SchwabTokenRefresh"
$ScriptPath = Join-Path $PSScriptRoot "refresh_token.py"
$PythonPath = (Get-Command python).Source

# Check if script exists
if (-not (Test-Path $ScriptPath)) {
    Write-Host "ERROR: Script not found at $ScriptPath" -ForegroundColor Red
    exit 1
}

Write-Host "Creating scheduled task: $TaskName" -ForegroundColor Cyan
Write-Host "Script: $ScriptPath" -ForegroundColor Gray
Write-Host "Python: $PythonPath" -ForegroundColor Gray
Write-Host ""

# Define the action (run Python script)
$Action = New-ScheduledTaskAction -Execute $PythonPath -Argument "`"$ScriptPath`"" -WorkingDirectory $PSScriptRoot

# Define the trigger (daily at 9:00 AM)
$Trigger = New-ScheduledTaskTrigger -Daily -At 9:00AM

# Define settings
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10)

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
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $Action `
        -Trigger $Trigger `
        -Settings $Settings `
        -Principal $Principal `
        -Description "Automatically refresh Schwab API token daily to prevent expiration"
    
    Write-Host "✓ Scheduled task created successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Task Details:" -ForegroundColor Cyan
    Write-Host "  Name: $TaskName"
    Write-Host "  Schedule: Daily at 9:00 AM"
    Write-Host "  Script: $ScriptPath"
    Write-Host ""
    Write-Host "The task will run automatically every day." -ForegroundColor Green
    Write-Host "You can also run it manually from Task Scheduler or by running:" -ForegroundColor Gray
    Write-Host "  python refresh_token.py" -ForegroundColor Yellow
    Write-Host ""
    
    # Ask if user wants to run it now
    $RunNow = Read-Host "Would you like to test the refresh now? (Y/N)"
    if ($RunNow -eq "Y" -or $RunNow -eq "y") {
        Write-Host ""
        Write-Host "Running token refresh..." -ForegroundColor Cyan
        & $PythonPath $ScriptPath
    }
    
} catch {
    Write-Host "ERROR: Failed to create scheduled task" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

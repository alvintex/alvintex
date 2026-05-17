param(
    [string]$TaskName = "ActiveETFTrackerDaily",
    [string]$ProjectRoot = (Resolve-Path "$PSScriptRoot\..").Path,
    [string]$Time = "18:30"
)

$python = (Get-Command python -ErrorAction Stop).Source
$script = Join-Path $ProjectRoot "scripts\run_daily_auto.py"
$logDir = Join-Path $ProjectRoot "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$action = New-ScheduledTaskAction `
    -Execute $python `
    -Argument "`"$script`" *> `"$logDir\daily-auto.log`"" `
    -WorkingDirectory $ProjectRoot

$trigger = New-ScheduledTaskTrigger -Daily -At $Time
$settings = New-ScheduledTaskSettingsSet `
    -MultipleInstances IgnoreNew `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Fetch active ETF holdings and rebuild local public data." `
    -Force | Out-Null

Write-Host "Installed scheduled task '$TaskName' at $Time."
Write-Host "Project: $ProjectRoot"
Write-Host "Log: $logDir\daily-auto.log"

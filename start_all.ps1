# Screen Time Dashboard - 启动脚本
# 同时启动 server 和 tracker，避免互相误杀
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "[ScreenTime] Starting..." -ForegroundColor Cyan

# 1. Start tracker (if not already running)
$trackerRunning = Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.Id -ne $pid }
$trackerPid = $null
if (-not $trackerRunning) {
    Write-Host "[Tracker] Starting..." -ForegroundColor Green
    $proc = Start-Process python -ArgumentList "tracker.py" -PassThru -WindowStyle Hidden
    $trackerPid = $proc.Id
    Start-Sleep -Seconds 1
} else {
    Write-Host "[Tracker] Already running" -ForegroundColor Yellow
}

# 2. Kill old server if any
netstat -ano | Select-String ":19999" | Select-String "LISTENING" | ForEach-Object {
    $line = $_ -replace '\s+', ' '
    $parts = $line.Split(' ')
    $pid = $parts[-1]
    if ($pid -match '^\d+$') {
        Write-Host "[Server] Killing old process PID=$pid" -ForegroundColor Yellow
        taskkill /PID $pid /F 2>$null
        Start-Sleep -Seconds 1
    }
}

# 3. Start server
Write-Host "[Server] Starting on port 19999..." -ForegroundColor Green
$script:serverProc = Start-Process python -ArgumentList "server.py" -PassThru -WindowStyle Hidden
$serverPid = $script:serverProc.Id
Start-Sleep -Seconds 2

# 4. Verify
netstat -ano | Select-String ":19999.*LISTENING" | Out-Null
if ($LASTEXITCODE -eq 0 -or $?) {
    Write-Host "[ScreenTime] All started. Server: http://127.0.0.1:19999" -ForegroundColor Cyan
} else {
    Write-Host "[ScreenTime] WARNING: Server may not have started. Check logs." -ForegroundColor Red
}

# 5. Open browser
Start-Process "http://127.0.0.1:19999"

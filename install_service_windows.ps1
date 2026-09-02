# install_service_windows.ps1
# Installs the bot and dashboard as Windows services using NSSM.
# Run as Administrator in PowerShell.
# Download NSSM from https://nssm.cc/download and place nssm.exe in this folder.

param(
    [string]$NssmPath = "$PSScriptRoot\nssm.exe"
)

$BotDir    = $PSScriptRoot
$Python    = "$BotDir\.venv\Scripts\python.exe"
$Streamlit = "$BotDir\.venv\Scripts\streamlit.exe"

if (-not (Test-Path $NssmPath)) {
    Write-Host "nssm.exe not found. Download from https://nssm.cc/download and place in $BotDir" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $Python)) {
    Write-Host "Virtual environment not found. Run setup.bat first." -ForegroundColor Red
    exit 1
}

Write-Host "Installing crypto-bot service..." -ForegroundColor Cyan
& $NssmPath install crypto-bot $Python "$BotDir\main.py"
& $NssmPath set crypto-bot AppDirectory $BotDir
& $NssmPath set crypto-bot AppStdout "$BotDir\bot.log"
& $NssmPath set crypto-bot AppStderr "$BotDir\bot.log"
& $NssmPath set crypto-bot Start SERVICE_AUTO_START

Write-Host "Installing crypto-dashboard service..." -ForegroundColor Cyan
& $NssmPath install crypto-dashboard $Streamlit "run dashboard.py --server.port 8501 --server.headless true"
& $NssmPath set crypto-dashboard AppDirectory $BotDir
& $NssmPath set crypto-dashboard Start SERVICE_AUTO_START

Write-Host "Starting services..." -ForegroundColor Cyan
& $NssmPath start crypto-bot
& $NssmPath start crypto-dashboard

Write-Host ""
Write-Host "Done! Services installed and started." -ForegroundColor Green
Write-Host "Bot logs: $BotDir\bot.log"
Write-Host "Dashboard: http://localhost:8501"
Write-Host ""
Write-Host "Useful commands:"
Write-Host "  Stop:    nssm stop crypto-bot"
Write-Host "  Start:   nssm start crypto-bot"
Write-Host "  Restart: nssm restart crypto-bot"
Write-Host "  Remove:  nssm remove crypto-bot confirm"

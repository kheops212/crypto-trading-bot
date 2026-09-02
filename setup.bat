@echo off
echo Setting up Crypto Trading Bot...
cd /d "%~dp0"

:: Find a working Python (prefer the py launcher, avoids the MS Store stub)
set PYTHON_CMD=
py --version >nul 2>&1
if not errorlevel 1 set PYTHON_CMD=py
if not defined PYTHON_CMD (
    python --version >nul 2>&1
    if not errorlevel 1 set PYTHON_CMD=python
)
if not defined PYTHON_CMD (
    echo Python not found. Please install Python 3.10+ from https://python.org
    echo During install, check "Add Python to PATH".
    pause
    exit /b 1
)

:: Create virtual environment
echo Creating virtual environment with %PYTHON_CMD%...
%PYTHON_CMD% -m venv .venv

:: Install dependencies
echo Installing dependencies...
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\pip install -r requirements.txt

:: Copy .env if it doesn't exist
if not exist .env (
    copy .env.example .env
    echo.
    echo .env file created. Please edit it with your API keys before running the bot.
)

echo.
echo Setup complete!
echo.
echo Next steps:
echo   1. Edit .env with your API keys
echo   2. Double-click run_bot.bat to start the bot
echo   3. Double-click run_dashboard.bat to open the dashboard
echo.
pause

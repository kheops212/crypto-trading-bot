@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\streamlit.exe (
    echo Virtual environment not found. Run setup.bat first.
    pause
    exit /b 1
)
.venv\Scripts\streamlit run dashboard.py --server.port 8501
pause

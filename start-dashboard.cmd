@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Run setup.cmd first to create the Python environment.
    pause
    exit /b 1
)
.venv\Scripts\python.exe -m streamlit run app.py
pause

@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
    if errorlevel 1 goto :error
)
.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
if errorlevel 1 goto :error
echo.
echo Setup complete. Run start-dashboard.cmd to open CommerceLens.
pause
exit /b 0
:error
echo Setup failed. Check that Python 3.12 or newer is installed and on PATH.
pause
exit /b 1

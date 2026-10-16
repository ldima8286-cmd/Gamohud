@echo off
REM Run gamohud-run from source on Windows (automatically sets up a local .venv and dependencies on first run).
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment (.venv)...
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment. Ensure Python 3.10+ is installed.
        pause
        exit /b 1
    )
)

set "PY=.venv\Scripts\python.exe"
"%PY%" -c "import PySide6, yaml, psutil" >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies (first run, may take a minute)...
    "%PY%" -m pip install --upgrade pip >nul 2>&1
    "%PY%" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies.
        pause
        exit /b 1
    )
)

"%PY%" "src\run_wrapper.py" %*
endlocal

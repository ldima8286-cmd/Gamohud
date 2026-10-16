@echo off
REM One-command installer for Gamohud on Windows.
REM
REM From a cloned repo: install.bat
setlocal
cd /d "%~dp0"

set "REPO=%~dp0"

echo Setting up Python environment...
if not exist "%REPO%\.venv\Scripts\python.exe" (
    python -m venv "%REPO%\.venv"
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment. Ensure Python 3.10+ is installed.
        pause
        exit /b 1
    )
)

set "PY=%REPO%\.venv\Scripts\python.exe"
"%PY%" -c "import PySide6, yaml, psutil" >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    "%PY%" -m pip install --upgrade pip >nul 2>&1
    "%PY%" -m pip install -r "%REPO%requirements.txt"
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies.
        pause
        exit /b 1
    )
)

echo Done.
echo You can run: run-gui.bat or create a shortcut to run-gui.bat.
pause
endlocal

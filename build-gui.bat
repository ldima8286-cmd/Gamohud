@echo off
REM Build the Gamohud desktop app with PyInstaller into dist\gamohud-gui.
REM Requires Python 3.10+ on PATH (or a .venv in this folder).
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    set "PY=.venv\Scripts\python.exe"
) else (
    echo Creating virtual environment (.venv)...
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment. Ensure Python 3.10+ is installed.
        pause
        exit /b 1
    )
    set "PY=.venv\Scripts\python.exe"
)

echo Using: %PY%
"%PY%" -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    "%PY%" -m pip install --upgrade pip >nul 2>&1
    "%PY%" -m pip install pyinstaller PySide6-Essentials PyYAML psutil
    if errorlevel 1 exit /b 1
)

"%PY%" -m PyInstaller --noconfirm gamohud-gui.spec %*
if errorlevel 1 exit /b 1

echo.
echo Build complete: dist\gamohud-gui\gamohud-gui.exe
endlocal

@echo off
REM Build the Gamohud desktop app with PyInstaller into dist\gamohud-gui.
REM Requires Python 3.10+ on PATH (or a .venv in this folder).
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    set "PY=.venv\Scripts\python.exe"
) else (
    set "PY=python"
)

echo Using: %PY%
"%PY%" -m pip install --upgrade pip >nul
"%PY%" -m pip install pyinstaller PySide6-Essentials pyyaml psutil
if errorlevel 1 exit /b 1

"%PY%" -m PyInstaller --noconfirm gamohud-gui.spec %*
if errorlevel 1 exit /b 1

echo.
echo Build complete: dist\gamohud-gui\gamohud-gui.exe
endlocal

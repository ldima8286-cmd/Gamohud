@echo off
REM Run Gamohud from source on Windows (no build required).
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    set "PY=.venv\Scripts\python.exe"
) else (
    set "PY=python"
)

"%PY%" "src\app.py" %*
endlocal

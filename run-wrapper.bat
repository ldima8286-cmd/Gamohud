@echo off
REM Dev launcher for gamohud-run on Windows (applies profiles / FPS backends).
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    set "PY=.venv\Scripts\python.exe"
) else (
    set "PY=python"
)

"%PY%" "src\run_wrapper.py" %*
endlocal

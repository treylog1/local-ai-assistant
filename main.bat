@echo off
cd /d "%~dp0"

REM Prefer a venv next to this script, then the parent-folder venv
if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" main.py
) else if exist "%~dp0..\.venv\Scripts\python.exe" (
    "%~dp0..\.venv\Scripts\python.exe" main.py
) else (
    echo No virtual environment found.
    echo Create one first:
    echo   python -m venv .venv
    echo   .\.venv\Scripts\Activate.ps1
    echo   pip install -r requirements.txt
    echo.
    python main.py
)

pause

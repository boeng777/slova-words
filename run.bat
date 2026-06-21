@echo off
REM Start the vocab trainer on Windows (double-click this file).
REM Checks Python, creates a virtual env, installs deps, starts the server.
cd /d "%~dp0"

set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY (
  where python >nul 2>nul && set "PY=python"
)
if not defined PY (
  echo [X] Python not found. Install it from https://www.python.org/downloads/
  echo     IMPORTANT: tick "Add Python to PATH" during installation.
  pause
  exit /b 1
)

if not exist .venv (
  echo Creating virtual environment...
  %PY% -m venv .venv
)
call .venv\Scripts\activate.bat

if not exist .venv\.deps-ok (
  echo Installing dependencies...
  python -m pip install --upgrade pip >nul
  pip install -r requirements.txt
  if errorlevel 1 (
    echo [X] Failed to install dependencies. Check your internet connection.
    pause
    exit /b 1
  )
  echo ok> .venv\.deps-ok
)

echo.
echo [OK] Server is starting. Open in your browser:  http://127.0.0.1:8000
echo      To stop: close this window or press Ctrl+C.
echo.
python app.py
pause

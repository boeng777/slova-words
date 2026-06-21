@echo off
REM Build a standalone .exe so your friends do NOT need Python installed.
REM Result: dist\vocab-trainer.exe
cd /d "%~dp0"

set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY (
  where python >nul 2>nul && set "PY=python"
)
if not defined PY (
  echo [X] Python not found. Install it from https://www.python.org/downloads/
  pause
  exit /b 1
)

if not exist .venv (
  %PY% -m venv .venv
)
call .venv\Scripts\activate.bat

echo Installing dependencies and PyInstaller...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt pyinstaller
if errorlevel 1 (
  echo [X] Failed to install dependencies. Check your internet connection.
  pause
  exit /b 1
)

echo.
echo Building standalone .exe (this takes a couple of minutes)...
pyinstaller --onefile --noconfirm --name vocab-trainer --icon app.ico --add-data "static;static" --collect-all uvicorn app.py
if errorlevel 1 (
  echo [X] Build failed.
  pause
  exit /b 1
)

echo.
echo [OK] Done: dist\vocab-trainer.exe
echo Give your friend ONLY that file. Progress is saved to a data\ folder next to the exe.
echo To run: double-click it, then open http://127.0.0.1:8000
pause

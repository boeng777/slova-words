@echo off
REM Stop the vocab trainer server (both the .exe build and "python app.py").
taskkill /IM vocab-trainer.exe /F >nul 2>nul
REM Also stop a python process holding port 8000 (dev mode), if any.
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8000" ^| findstr LISTENING') do taskkill /PID %%p /F >nul 2>nul
echo Server stopped (if it was running).
timeout /t 2 >nul

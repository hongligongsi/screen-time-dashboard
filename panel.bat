@echo off
chcp 65001 >nul
cd /d "%~dp0"

rem Start tracker if not already running
tasklist /FI "IMAGENAME eq pythonw.exe" 2>nul | find /I "pythonw" >nul
if %errorlevel% neq 0 (
    start "" pythonw tracker.py
    timeout /t 2 /nobreak >nul
)

rem Start server if not already listening
netstat -an | findstr ":19999.*LISTEN" >nul
if %errorlevel% neq 0 (
    start "" pythonw server.py
    timeout /t 3 /nobreak >nul
)
start "" http://127.0.0.1:19999

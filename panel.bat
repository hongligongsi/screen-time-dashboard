@echo off
chcp 65001 >nul
cd /d "%~dp0"
netstat -an | findstr ":19999.*LISTEN" >nul
if %errorlevel% neq 0 (
    start "" pythonw server.py
    timeout /t 3 /nobreak >nul
)
start "" http://127.0.0.1:19999

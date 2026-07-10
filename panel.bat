@echo off
chcp 65001 >nul
cd /d "%~dp0"

rem Kill any stuck pythonw processes first
taskkill /F /IM pythonw.exe /T 2>nul
timeout /t 1 /nobreak >nul

rem Start tracker (hidden window)
start "" /B pythonw.exe tracker.py
timeout /t 2 /nobreak >nul

rem Start server (hidden window)
start "" /B pythonw.exe server.py
timeout /t 3 /nobreak >nul

rem Open browser
start "" http://127.0.0.1:19999

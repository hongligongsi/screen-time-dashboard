@echo off
chcp 65001 >nul
cd /d "%~dp0"

:: 启动后台采集（静默运行，不弹黑窗）
start "" /B pythonw.exe tracker.py

:: 等待1秒让采集启动
timeout /t 1 /nobreak >nul

:: 启动Web面板
start "" pythonw.exe server.py

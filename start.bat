@echo off
cd /d "%~dp0"
if not exist .venv (
    call setup.bat
)
.venv\Scripts\python main.py
pause

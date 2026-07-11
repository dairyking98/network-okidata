@echo off
REM Set up a venv and install dependencies (Windows).
cd /d "%~dp0"

python -m venv .venv
.venv\Scripts\pip install --upgrade pip
.venv\Scripts\pip install -r requirements.txt

echo.
echo Setup complete. Run the app with:
echo   .venv\Scripts\python main.py

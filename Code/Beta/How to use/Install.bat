@echo off
echo ===========================================
echo   Python Libraries Installation
echo ===========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python first.
    pause
    exit /b
)

echo [INFO] Installing required libraries...
echo.

REM Optional: Upgrade pip
python -m pip install --upgrade pip

REM Install required libraries
pip install pyserial pyqt6 keyboard gputil psutil

echo.
echo ===========================================
echo   Installation completed!
echo ===========================================
pause

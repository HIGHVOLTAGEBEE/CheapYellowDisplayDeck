@echo off
echo ===========================================
echo   Python Bibliotheken Installation
echo ===========================================
echo.

REM Prüfen, ob Python installiert ist
python --version >nul 2>&1
if errorlevel 1 (
    echo [FEHLER] Python wurde nicht gefunden. Bitte installiere Python zuerst.
    pause
    exit /b
)

echo [INFO] Installiere benötigte Bibliotheken...
echo.

REM Optional: Upgrade von pip
python -m pip install --upgrade pip

REM Installation der benötigten Bibliotheken
pip install pyserial pyqt6 keyboard

echo.
echo ===========================================
echo   Installation abgeschlossen!
echo ===========================================
pause

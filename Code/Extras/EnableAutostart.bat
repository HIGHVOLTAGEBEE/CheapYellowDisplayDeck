@echo off
:: Starte eine Verknüpfung
start "" "%USERPROFILE%\Desktop\CYDDECK.lnk"

:: Pfad zum Autostart-Ordner
set AUTOSTART=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup

:: Kopiere sich selbst in den Autostart-Ordner
if not exist "%AUTOSTART%\startme.bat" (
    copy "%~f0" "%AUTOSTART%\startme.bat" >nul
)

exit

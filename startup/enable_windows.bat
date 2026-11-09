@echo off
REM ==============================================================================
REM TimeTracker v2 - Enable Startup on Windows
REM Adds a silent background launcher to the user's Startup folder.
REM ==============================================================================

setlocal enabledelayedexpansion

set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "LAUNCHER_VBS=%STARTUP_DIR%\TimeTrackerStartup.vbs"

echo [TimeTracker] Configuring Windows startup launcher...

REM Create a VBS script that runs the daemon completely silently (no console window popup)
(
    echo Set WshShell = CreateObject^("WScript.Shell"^)
    echo WshShell.Run "pythonw -m timetracker.daemon", 0, False
) > "%LAUNCHER_VBS%"

if exist "%LAUNCHER_VBS%" (
    echo [OK] Startup script created: %LAUNCHER_VBS%
    echo [OK] TimeTracker will now start silently in the background on user logon.
) else (
    echo [Error] Failed to create startup file in %STARTUP_DIR%
    exit /b 1
)

endlocal

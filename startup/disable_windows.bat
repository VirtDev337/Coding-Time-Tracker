@echo off
REM ==============================================================================
REM TimeTracker v2 - Disable Startup on Windows
REM Removes the background launcher from the user's Startup folder.
REM ==============================================================================

setlocal enabledelayedexpansion

set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "LAUNCHER_VBS=%STARTUP_DIR%\TimeTrackerStartup.vbs"
set "LAUNCHER_BAT=%STARTUP_DIR%\TimeTrackerStartup.bat"

echo [TimeTracker] Disabling Windows startup launcher...

if exist "%LAUNCHER_VBS%" (
    del /f /q "%LAUNCHER_VBS%"
    echo [OK] Removed %LAUNCHER_VBS%
)

if exist "%LAUNCHER_BAT%" (
    del /f /q "%LAUNCHER_BAT%"
    echo [OK] Removed %LAUNCHER_BAT%
)

echo [OK] TimeTracker startup disabled on Windows.
endlocal

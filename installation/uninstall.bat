@echo off
REM ==============================================================================
REM TimeTracker v2 - Windows Uninstaller
REM Stops background daemon, removes shortcuts, wrappers, and virtual environment.
REM ==============================================================================

setlocal enabledelayedexpansion

echo =======================================================
echo          TimeTracker v2 - Windows Uninstaller
echo =======================================================
echo.

REM 1. Stop background processes
echo Stopping any running TimeTracker processes...
taskkill /F /IM pythonw.exe /FI "WINDOWTITLE eq TimeTracker*" >nul 2>&1
taskkill /F /FI "COMMANDLINE eq *timetracker*" >nul 2>&1

REM 2. Remove Shortcuts
echo Removing Desktop and Start Menu shortcuts...
if exist "%USERPROFILE%\Desktop\TimeTracker v2.lnk" del /F /Q "%USERPROFILE%\Desktop\TimeTracker v2.lnk"
if exist "%APPDATA%\Microsoft\Windows\Start Menu\Programs\TimeTracker v2.lnk" del /F /Q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\TimeTracker v2.lnk"

REM 3. Remove Startup entry
set "STARTUP_VBS=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\TimeTrackerStartup.vbs"
if exist "%STARTUP_VBS%" del /F /Q "%STARTUP_VBS%"
set "STARTUP_BAT=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\TimeTrackerStartup.bat"
if exist "%STARTUP_BAT%" del /F /Q "%STARTUP_BAT%"

REM 4. Remove installation files
set "INSTALL_DIR=%LOCALAPPDATA%\TimeTracker"
if exist "%INSTALL_DIR%" (
    echo Removing application files from %INSTALL_DIR%...
    rmdir /S /Q "%INSTALL_DIR%"
)

REM 5. Remove from User PATH
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$bin = [System.IO.Path]::GetFullPath('%LOCALAPPDATA%\TimeTracker\bin'); ^
     $userPath = [Environment]::GetEnvironmentVariable('Path', 'User'); ^
     if ($userPath) { ^
         $newPath = ($userPath -split ';' | Where-Object { $_ -ne $bin -and $_ -ne '' }) -join ';'; ^
         [Environment]::SetEnvironmentVariable('Path', $newPath, 'User'); ^
     }"

REM 6. Ask about Database
set "DB_DIR=%USERPROFILE%\.codetime"
if exist "%DB_DIR%" (
    echo.
    set /p DEL_DB="Do you also want to remove your tracking database (%DB_DIR%)? [y/N]: "
    if /i "!DEL_DB!"=="Y" (
        rmdir /S /Q "%DB_DIR%"
        echo Removed tracking database.
    ) else (
        echo Preserved tracking database at %DB_DIR%.
    )
)

echo.
echo [OK] TimeTracker v2 has been uninstalled successfully.
echo.
pause
endlocal
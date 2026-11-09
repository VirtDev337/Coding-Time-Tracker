@echo off
REM ==============================================================================
REM TimeTracker v2 - Standalone Windows Installer
REM Creates isolated environment, installs dependencies, sets up CLI wrappers,
REM Desktop shortcut, Start Menu shortcut, and autostart integration.
REM ==============================================================================

setlocal enabledelayedexpansion

echo =======================================================
echo          TimeTracker v2 - Windows Installer
echo =======================================================
echo.

REM 1. Locate Python 3
set "PY_CMD="
where py >nul 2>nul
if %errorlevel% equ 0 (
    set "PY_CMD=py -3"
) else (
    where python >nul 2>nul
    if %errorlevel% equ 0 (
        set "PY_CMD=python"
    )
)

if "%PY_CMD%"=="" (
    echo [ERROR] Python 3 was not found on your system!
    echo Please install Python 3.8 or higher from https://www.python.org/downloads/
    echo or run in PowerShell: winget install Python.Python.3.11
    echo Be sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo [1/5] Found Python: %PY_CMD%

REM 2. Define Destination Paths
set "SCRIPT_DIR=%~dp0"
REM Remove trailing backslash if present
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
for %%I in ("%SCRIPT_DIR%\..") do set "PROJECT_ROOT=%%~dpnxfI"

set "INSTALL_DIR=%LOCALAPPDATA%\TimeTracker"
set "VENV_DIR=%INSTALL_DIR%\venv"
set "BIN_DIR=%INSTALL_DIR%\bin"

echo [2/5] Creating application environment at %INSTALL_DIR%...
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
if not exist "%BIN_DIR%" mkdir "%BIN_DIR%"

if not exist "%VENV_DIR%" (
    %PY_CMD% -m venv "%VENV_DIR%"
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

REM 3. Install TimeTracker and Dependencies
echo [3/5] Installing dependencies and TimeTracker package...
"%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip >nul 2>&1
"%VENV_DIR%\Scripts\pip.exe" install -e "%PROJECT_ROOT%"
if %errorlevel% neq 0 (
    echo [ERROR] pip install failed.
    pause
    exit /b 1
)

REM Copy icon asset
if exist "%PROJECT_ROOT%\assets\icon.jpg" (
    copy /Y "%PROJECT_ROOT%\assets\icon.jpg" "%INSTALL_DIR%\icon.jpg" >nul
)

REM 4. Create Command Line Wrappers (.cmd)
echo [4/5] Creating executable wrappers in %BIN_DIR%...

(
    echo @echo off
    echo "%VENV_DIR%\Scripts\python.exe" -m timetracker.cli %%*
) > "%BIN_DIR%\timetracker.cmd"

(
    echo @echo off
    echo start "" "%VENV_DIR%\Scripts\pythonw.exe" -m timetracker.gui %%*
) > "%BIN_DIR%\timetracker-gui.cmd"

(
    echo @echo off
    echo start "" "%VENV_DIR%\Scripts\pythonw.exe" -m timetracker.daemon %%*
) > "%BIN_DIR%\timetracker-daemon.cmd"

REM Add BIN_DIR to User PATH if not present
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$bin = [System.IO.Path]::GetFullPath('%BIN_DIR%'); ^
     $userPath = [Environment]::GetEnvironmentVariable('Path', 'User'); ^
     if ($userPath -split ';' -notcontains $bin) { ^
         [Environment]::SetEnvironmentVariable('Path', $userPath + ';' + $bin, 'User'); ^
         Write-Host '  [+] Added %BIN_DIR% to User PATH' ^
     }"

REM 5. Create Desktop & Start Menu Shortcuts via PowerShell
echo [5/5] Creating Desktop and Start Menu shortcuts...

set "DESKTOP_DIR=%USERPROFILE%\Desktop"
set "STARTMENU_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$wsh = New-Object -ComObject WScript.Shell; ^
     $shortcut = $wsh.CreateShortcut('%DESKTOP_DIR%\TimeTracker v2.lnk'); ^
     $shortcut.TargetPath = '%BIN_DIR%\timetracker-gui.cmd'; ^
     $shortcut.WorkingDirectory = '%INSTALL_DIR%'; ^
     $shortcut.Description = 'TimeTracker v2 - Ambient Developer Time Tracking'; ^
     $shortcut.Save(); ^
     $menuShortcut = $wsh.CreateShortcut('%STARTMENU_DIR%\TimeTracker v2.lnk'); ^
     $menuShortcut.TargetPath = '%BIN_DIR%\timetracker-gui.cmd'; ^
     $menuShortcut.WorkingDirectory = '%INSTALL_DIR%'; ^
     $menuShortcut.Description = 'TimeTracker v2 - Ambient Developer Time Tracking'; ^
     $menuShortcut.Save();"

REM Ask to configure autostart
echo.
set /p AUTOSTART_CHOICE="Would you like TimeTracker to start automatically at login? [Y/n]: "
if /i "%AUTOSTART_CHOICE%"=="Y" (
    call "%PROJECT_ROOT%\startup\enable_windows.bat"
) else if "%AUTOSTART_CHOICE%"=="" (
    call "%PROJECT_ROOT%\startup\enable_windows.bat"
)

echo.
echo =======================================================
echo     TimeTracker v2 Installation Successful!
echo =======================================================
echo.
echo Available Commands (open a new Command Prompt or PowerShell):
echo   timetracker status       - View today's tracking status
echo   timetracker gui          - Launch desktop interface
echo   timetracker projects     - List tracked projects
echo   timetracker report       - Generate customized PDF report
echo.
echo Desktop shortcut created: "TimeTracker v2"
echo.
pause
endlocal
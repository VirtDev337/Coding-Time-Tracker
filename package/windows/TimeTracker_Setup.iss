; ==============================================================================
; TimeTracker v2 - Inno Setup Compiler Script
; Compiles a professional Windows installer executable (.exe)
; ==============================================================================

#define MyAppName "TimeTracker v2"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "VirtDev"
#define MyAppURL "https://github.com/VirtDev337"
#define MyAppExeName "timetracker-gui.cmd"

[Setup]
AppId={{7B8B7A42-4F11-45D3-8E5A-64D0F8E3C3E1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\TimeTracker
DisableProgramGroupPage=yes
OutputBaseFilename=TimeTracker_v2_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
OutputDir=..\..\dist

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "autostart"; Description: "Start TimeTracker automatically at login (silent background tracking)"; GroupDescription: "Startup Options:"

[Files]
Source: "..\..\src\*"; DestDir: "{app}\src"; Flags: recursesubdirs createallsubdirs
Source: "..\..\assets\*"; DestDir: "{app}\assets"; Flags: recursesubdirs createallsubdirs
Source: "..\..\installation\*"; DestDir: "{app}\installation"; Flags: recursesubdirs createallsubdirs
Source: "..\..\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\pyproject.toml"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\setup.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\startup\*"; DestDir: "{app}\startup"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\bin\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\bin\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{cmd}"; Parameters: "/c cd /d ""{app}"" && py -3 -m venv ""{app}\venv"" && ""{app}\venv\Scripts\pip.exe"" install -e ."; StatusMsg: "Installing dependencies and configuring virtual environment..."; Flags: runhidden
Filename: "{cmd}"; Parameters: "/c if not exist ""{app}\bin"" mkdir ""{app}\bin"" && (echo @echo off & echo start """" ""{app}\venv\Scripts\pythonw.exe"" -m timetracker.gui %%%%*) > ""{app}\bin\timetracker-gui.cmd"" && (echo @echo off & echo start """" ""{app}\venv\Scripts\pythonw.exe"" -m timetracker.daemon %%%%*) > ""{app}\bin\timetracker-daemon.cmd"" && (echo @echo off & echo ""{app}\venv\Scripts\python.exe"" -m timetracker.cli %%%%*) > ""{app}\bin\timetracker.cmd"""; StatusMsg: "Creating command-line and GUI wrappers..."; Flags: runhidden
Filename: "{app}\startup\enable_windows.bat"; Tasks: autostart; Flags: runhidden; StatusMsg: "Configuring automatic background tracking at login..."

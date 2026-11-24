; Build on Windows after Python/PyInstaller creates dist\AuroraDesktop.
#define MyAppName "Aurora"
#define MyAppVersion "0.1.0"
#define MyAppExeName "AuroraDesktop.exe"

[Setup]
AppId={{A69F08CF-3CF7-4395-ACBC-66865A5D7FE7}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={localappdata}\Programs\Aurora
DefaultGroupName=Aurora
PrivilegesRequired=lowest
OutputDir=..\..\..\dist
OutputBaseFilename=Aurora-Setup-Windows-x64
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\AuroraDesktop.exe

[Files]
Source: "..\..\..\dist\AuroraDesktop\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Aurora"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Aurora"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Aurora"; Flags: nowait postinstall skipifsilent

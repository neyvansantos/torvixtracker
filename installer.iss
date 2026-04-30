[Setup]
AppName=Torvix Tracker
AppVersion=0.1.4
DefaultDirName={pf}\TorvixTracker
DefaultGroupName=Torvix Tracker
OutputDir=installer
OutputBaseFilename=TorvixInstaller
Compression=lzma
SolidCompression=yes

[Files]
Source: "dist\TorvixTracker.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Torvix Tracker"; Filename: "{app}\TorvixTracker.exe"
Name: "{userdesktop}\Torvix Tracker"; Filename: "{app}\TorvixTracker.exe"

[Run]
Filename: "{app}\TorvixTracker.exe"; Description: "Abrir Torvix Tracker"; Flags: nowait postinstall skipifsilent
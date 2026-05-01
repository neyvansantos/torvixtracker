; Copyright (c) 2026 Torvix Tracker. Todos os direitos reservados.
[Setup]
AppName=Torvix Tracker
AppVersion=0.1.4
AppCopyright=Copyright (c) 2026 Torvix Tracker. Todos os direitos reservados.
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

; Copyright (c) 2026 Torvix Tracker. Todos os direitos reservados.
; Script gerado pelo Antigravity para o Torvix Tracker
#define AppName "Torvix Tracker"
#define AppVersion "0.1.4"
#define AppPublisher "Torvix Tracker"
#define AppURL "https://github.com/NeyvanSantos/TorvixTracker"
#define AppExeName "TorvixTracker.exe"

[Setup]
; NOTA: O valor de AppId identifica exclusivamente este aplicativo.
; No use o mesmo valor de AppId em instaladores de outros aplicativos.
AppId={{C7892E52-2706-49AF-9C3C-FE8645D838DF}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppCopyright=Copyright (c) 2026 Torvix Tracker. Todos os direitos reservados.
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={localappdata}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
; Remova a linha abaixo para rodar em modo administrativo (não recomendado para este app)
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=TorvixTracker_Setup
SetupIconFile=..\assets\icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\TorvixTracker\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
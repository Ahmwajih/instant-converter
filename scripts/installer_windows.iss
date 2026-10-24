#define MyAppName "Instant Converter"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Instant Converter Contributors"
#define MyAppExeName "InstantConverter.exe"

[Setup]
AppId={{8D4E9C6F-51B3-4F2A-9B0E-3C8A7F6E5D11}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
OutputDir=..\dist
OutputBaseFilename=InstantConverter-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\assets\icon.ico
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "contextmenu"; Description: "Add 'Convert with Instant Converter' to Windows Explorer right-click menu"; GroupDescription: "Shell Integration:"

[Files]
Source: "..\dist\InstantConverter\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Classes\*\shell\InstantConverter"; ValueType: string; ValueName: ""; ValueData: "Convert with Instant Converter"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\*\shell\InstantConverter"; ValueType: string; ValueName: "Icon"; ValueData: """{app}\{#MyAppExeName}"""; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\*\shell\InstantConverter\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: contextmenu

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

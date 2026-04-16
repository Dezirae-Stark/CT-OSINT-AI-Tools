; GhostExodus OSINT Platform — Inno Setup Installer Script
; Build with: iscc installer\ghostexodus.iss
; Requires: Inno Setup 6+ (https://jrsoftware.org/isinfo.php)
;
; The PyInstaller --onedir bundle must already be built at:
;   dist\GhostExodus\
; before running this script.

#define AppName         "GhostExodus OSINT Platform"
#define AppVersion      "1.0.0"
#define AppPublisher    "CT-OSINT Intelligence"
#define AppURL          "https://github.com/Dezirae-Stark/CT-OSINT-AI-Tools"
#define AppExeName      "GhostExodus.exe"
#define AppDataDir      "{userappdata}\GhostExodus"

[Setup]
AppId={{A8F3B2C1-7E4D-4F9A-B2C3-D4E5F6A7B8C9}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} v{#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={autopf}\GhostExodus
DefaultGroupName=GhostExodus
AllowNoIcons=yes
; Require admin for installation to Program Files
PrivilegesRequired=admin
OutputDir=installer\output
OutputBaseFilename=GhostExodus_Setup_v{#AppVersion}
; Compression
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes
LZMADictionarySize=524288
; Appearance
WizardStyle=modern
WizardSizePercent=120
; Windows 10/11 only
MinVersion=10.0.17763
; 64-bit only
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
; Uninstall
UninstallDisplayIcon={app}\GhostExodus.exe
UninstallDisplayName={#AppName}
; Allow running app after install
DisableFinishedPage=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon";    Description: "{cm:CreateDesktopIcon}";    GroupDescription: "{cm:AdditionalIcons}"
Name: "startupicon";   Description: "Start GhostExodus on Windows startup"; GroupDescription: "Startup"

[Files]
; Main application bundle (PyInstaller --onedir output)
Source: "..\dist\GhostExodus\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Environment template (if not already present in install dir)
Source: "..\env.example";        DestDir: "{app}"; DestName: ".env.example"; Flags: ignoreversion

; Custom Ollama analyst model definition
Source: "..\ghostexodus.Modelfile"; DestDir: "{app}"; Flags: ignoreversion

; Model setup script (pulls base model + builds ghostexodus-analyst)
Source: "..\installer\setup_models.bat"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
; Create writable data directories outside Program Files
; (Program Files is read-only on Windows — data must go in AppData or next to exe)
Name: "{#AppDataDir}\data\chromadb"
Name: "{#AppDataDir}\data\sqlite"
Name: "{#AppDataDir}\data\evidence"
Name: "{#AppDataDir}\data\evidence\media"
Name: "{#AppDataDir}\data\reports"

[Icons]
Name: "{group}\{#AppName}";                    Filename: "{app}\{#AppExeName}";        WorkingDir: "{#AppDataDir}"
Name: "{group}\Setup AI Model";                Filename: "{app}\setup_models.bat";     WorkingDir: "{app}"; Comment: "Download and configure the GhostExodus analyst model (requires internet)"
Name: "{group}\Uninstall {#AppName}";          Filename: "{uninstallexe}"
Name: "{commondesktop}\{#AppName}";            Filename: "{app}\{#AppExeName}";        WorkingDir: "{#AppDataDir}";  Tasks: desktopicon

[Registry]
; Startup registry entry (optional task)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
  ValueType: string; ValueName: "GhostExodus"; \
  ValueData: """{app}\{#AppExeName}"""; \
  Flags: uninsdeletevalue; Tasks: startupicon

[Run]
; Download base model + build ghostexodus-analyst (optional — requires internet + Ollama)
Filename: "{app}\setup_models.bat"; Description: "Download and configure AI analyst model (ghostexodus-analyst, ~4.7 GB — requires Ollama + internet)"; Flags: postinstall skipifsilent nowait unchecked

; Open install dir after install
Filename: "{app}"; Description: "Open installation folder"; Flags: postinstall skipifsilent shellexec

; Launch the app after install
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; Flags: postinstall skipifsilent nowait

[UninstallDelete]
; Remove data directory on uninstall (optional — comment out to preserve data)
; Type: filesandordirs; Name: "{#AppDataDir}"

[Code]
// ─── Prerequisite checks ─────────────────────────────────────────────────────

function OllamaInstalled(): Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec('cmd.exe', '/C where ollama >nul 2>&1', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Result := Result and (ResultCode = 0);
end;

function InitializeSetup(): Boolean;
begin
  Result := True;

  // Warn if Ollama is not found
  if not OllamaInstalled() then
  begin
    if MsgBox(
      'Ollama was not found on this system.' + #13#10 + #13#10 +
      'GhostExodus requires Ollama to run the AI analysis engine.' + #13#10 +
      'The custom model "ghostexodus-analyst" (based on llama3.1:8b) will be' + #13#10 +
      'configured by the Setup AI Model script included with this installer.' + #13#10 + #13#10 +
      'Install Ollama first from: https://ollama.com' + #13#10 +
      'Then run: Start Menu > GhostExodus > Setup AI Model' + #13#10 + #13#10 +
      'Continue installation anyway?',
      mbConfirmation, MB_YESNO) = IDNO
    then
      Result := False;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  EnvSource, EnvDest: String;
begin
  if CurStep = ssPostInstall then
  begin
    // Copy .env.example to AppData as .env if it doesn't already exist
    EnvSource := ExpandConstant('{app}\.env.example');
    EnvDest   := ExpandConstant('{#AppDataDir}\.env');
    if not FileExists(EnvDest) then
      FileCopy(EnvSource, EnvDest, False);
  end;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  // On finish page, we don't need to do anything special
end;

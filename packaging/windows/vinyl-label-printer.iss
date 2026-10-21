; Inno Setup script for Vinyl Label Printer (per-user install, no admin rights).
;
; Build from the repository root after the PyInstaller build, passing the
; version from vinyl-label-printer/__version__.py:
;     ISCC /DAppVersion=0.4.0 packaging\windows\vinyl-label-printer.iss
; The CI windows job passes the package version from packaging/package_version.sh
; and the plain X.Y.Z separately, e.g. for the tag v1.0.0-rc.1:
;     ISCC /DAppVersion=1.0.0-rc.1 /DNumericVersion=1.0.0 packaging\windows\vinyl-label-printer.iss
; Output: dist\VinylLabelPrinterSetup-<AppVersion>.exe
;
; Requires Inno Setup 6.3 or newer. Saved as UTF-8 with BOM (German umlauts).

#if Ver < EncodeVer(6, 3, 0)
  #error Inno Setup 6.3 or newer is required (x64compatible architecture identifier)
#endif

#ifndef AppVersion
  #error AppVersion is not set. Pass it on the command line: ISCC /DAppVersion=x.y.z
#endif
; Version resource of the setup (file properties): numbers only, so a
; pre-release AppVersion such as 1.0.0-rc.1 needs NumericVersion=1.0.0.
#ifndef NumericVersion
  #define NumericVersion AppVersion
#endif

#define AppName      "Vinyl Label Printer"
#define AppExeName   "vinyl-label-printer.exe"
#define AppPublisher "EJAIS"
#define AppUrl       "https://github.com/EJAIS/vinylsticker"
; Same ID as main.py sets at runtime, so taskbar pins and the Start Menu
; shortcut belong to the same app.
#define AppUserModelId "EJAIS.VinylLabelPrinter"
#define RepoRoot     AddBackslash(SourcePath) + "..\.."

[Setup]
; AppId identifies the installation to Windows (upgrades, the uninstall entry
; in Settings → Apps). NEVER change it: a new AppId turns the next version into
; a second, separate installation instead of an upgrade.
AppId={{BFCF8A94-71A8-4613-99F2-B65DB1EA679E}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppUrl}
AppSupportURL={#AppUrl}/issues
AppUpdatesURL={#AppUrl}/releases
VersionInfoVersion={#NumericVersion}

; Per-user install: no UAC prompt, everything below the user profile.
PrivilegesRequired=lowest
DefaultDirName={localappdata}\Programs\{#AppName}
; Start Menu folder "Vinyl Label Printer" (the shortcut inside it is
; "Vinyl Label Printer.lnk"). The old script install put its own "Vinyl Label
; Printer.lnk" directly into Programs, so the two shortcuts never overwrite each
; other while a user switches over.
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; Upgrades: same AppId and the previous folder; a running app is closed via
; the Restart Manager (automatically in silent mode) before files are replaced.
UsePreviousAppDir=yes
CloseApplications=yes
CloseApplicationsFilter=*.exe,*.dll,*.pyd
RestartApplications=no

LicenseFile={#RepoRoot}\LICENSE
SetupIconFile={#RepoRoot}\packaging\icons\icon.ico
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName}
WizardStyle=modern
ShowLanguageDialog=auto

OutputDir={#RepoRoot}\dist
OutputBaseFilename=VinylLabelPrinterSetup-{#AppVersion}
Compression=lzma2/max
SolidCompression=yes

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "de"; MessagesFile: "compiler:Languages\German.isl"

[CustomMessages]
en.UserDataDirNotAllowed=This folder holds your Vinyl Label Printer data or an old script installation. Please choose a different folder.
de.UserDataDirNotAllowed=Dieser Ordner enthält Ihre Vinyl-Label-Drucker-Daten oder eine alte Skript-Installation. Bitte wählen Sie einen anderen Ordner.

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[InstallDelete]
; Remove the previous bundle before an upgrade so no stale libraries or Qt
; plugins from an older version stay next to the new ones. Only when {app}
; already holds our exe: an _internal folder of another app is never touched.
Type: filesandordirs; Name: "{app}\_internal"; Check: IsUpgradeOfThisApp

[Files]
Source: "{#RepoRoot}\dist\vinyl-label-printer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; AppUserModelID: "{#AppUserModelId}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; AppUserModelID: "{#AppUserModelId}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

; No [UninstallDelete] section on purpose: the uninstaller removes only the
; files and shortcuts this setup installed. User data, cache and logs in
; %APPDATA%\vinyl-label-printer and %LOCALAPPDATA%\vinyl-label-printer (also
; the program folder of the old script installs up to v0.4.0) are never touched.

[Code]
// Check for [InstallDelete]: {app} already contains this app's exe, i.e. this
// is an upgrade of an existing Vinyl Label Printer installation.
function IsUpgradeOfThisApp: Boolean;
begin
  Result := FileExists(ExpandConstant('{app}\{#AppExeName}'));
end;

// The app keeps its data in %APPDATA%\vinyl-label-printer and
// %LOCALAPPDATA%\vinyl-label-printer (also the program folder of the old
// script installs up to v0.4.0).
// Installing into one of them would mix program files with user data.
function IsInDir(const Path, Dir: String): Boolean;
var
  P, D: String;
begin
  P := Lowercase(AddBackslash(Path));
  D := Lowercase(AddBackslash(Dir));
  Result := Copy(P, 1, Length(D)) = D;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  Dir: String;
begin
  Result := True;
  if CurPageID = wpSelectDir then
  begin
    Dir := WizardDirValue;
    if IsInDir(Dir, ExpandConstant('{userappdata}\vinyl-label-printer')) or
       IsInDir(Dir, ExpandConstant('{localappdata}\vinyl-label-printer')) then
    begin
      SuppressibleMsgBox(CustomMessage('UserDataDirNotAllowed'), mbError, MB_OK, IDOK);
      Result := False;
    end;
  end;
end;

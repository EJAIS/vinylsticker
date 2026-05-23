#Requires -Version 5.1
<#
.SYNOPSIS
    Vinyl Label Printer — Install & Update Script for Windows
.DESCRIPTION
    Installs or updates Vinyl Label Printer on Windows 10/11.
    Handles fresh installation and updates automatically.
    User data (Datenbank.xlsx, settings, credentials) is
    preserved during updates.
.PARAMETER Uninstall
    Remove the application (keeps user data backup)
.EXAMPLE
    .\install.ps1
    .\install.ps1 -Uninstall
#>

param(
    [switch]$Uninstall
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Configuration ──────────────────────────────────────────────
$RepoOwner   = "EJAIS"
$RepoName    = "vinylsticker"
$RepoUrl     = "https://github.com/$RepoOwner/$RepoName"
$RepoApi     = "https://api.github.com/repos/$RepoOwner/$RepoName"
$AppSubDir   = "vinyl-label-printer"
$InstallDir  = Join-Path $env:LOCALAPPDATA "vinyl-label-printer"
$StartMenu   = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
$ShortcutPath = Join-Path $StartMenu "Vinyl Label Printer.lnk"
$BackupDir   = Join-Path $env:TEMP "vinyl-label-printer-backup-$(Get-Date -Format 'yyyyMMdd_HHmmss')"

# ── Colors / Output helpers ────────────────────────────────────
function Write-Info    { param($msg) Write-Host "  i  $msg" -ForegroundColor Cyan }
function Write-Success { param($msg) Write-Host "  v  $msg" -ForegroundColor Green }
function Write-Warn    { param($msg) Write-Host "  !  $msg" -ForegroundColor Yellow }
function Write-Err     { param($msg) Write-Host "  x  $msg" -ForegroundColor Red }
function Write-Header  { param($msg) Write-Host "`n$msg" -ForegroundColor White }
function Stop-Install  { param($msg) Write-Err $msg; exit 1 }

# ── Version helpers ────────────────────────────────────────────
function Get-InstalledVersion {
    $verFile = Join-Path $InstallDir "__version__.py"
    if (Test-Path $verFile) {
        $line = Select-String -Path $verFile -Pattern '__version__' |
                Select-Object -First 1
        if ($line -match '"([^"]+)"') { return $Matches[1] }
    }
    return ""
}

function Get-LatestVersion {
    try {
        $headers = @{ "Accept" = "application/vnd.github+json" }
        $releases = Invoke-RestMethod `
            -Uri "$RepoApi/releases" `
            -Headers $headers `
            -TimeoutSec 10
        if ($releases.Count -gt 0) {
            return $releases[0].tag_name.TrimStart('v')
        }
    } catch {
        Write-Warn "Konnte Version nicht von GitHub abrufen."
    }
    return ""
}

# ── Check Python ───────────────────────────────────────────────
function Test-Python {
    Write-Header "Pruefe Systemvoraussetzungen..."

    $python = $null
    foreach ($cmd in @("python", "python3", "py")) {
        try {
            $ver = & $cmd --version 2>&1
            if ($ver -match "Python (\d+)\.(\d+)") {
                $major = [int]$Matches[1]
                $minor = [int]$Matches[2]
                if ($major -ge 3 -and $minor -ge 10) {
                    $python = $cmd
                    Write-Success "Python $major.$minor gefunden ($cmd)"
                    break
                } else {
                    Write-Warn "Python $major.$minor zu alt (3.10+ erforderlich)"
                }
            }
        } catch { continue }
    }

    if (-not $python) {
        Write-Err "Python 3.10+ nicht gefunden."
        Write-Info "Bitte installieren von: https://www.python.org/downloads/"
        Write-Info "Wichtig: 'Add Python to PATH' bei der Installation aktivieren!"
        Start-Process "https://www.python.org/downloads/"
        Stop-Install "Python 3.10+ wird benoetigt."
    }

    return $python
}

# ── Check/Install Poppler ──────────────────────────────────────
function Install-Poppler {
    Write-Header "Pruefe Poppler (PDF-Vorschau)..."

    $popplerDir = Join-Path $InstallDir "poppler"
    $popplerBin = Join-Path $popplerDir "Library\bin"

    if (Test-Path (Join-Path $popplerBin "pdftoppm.exe")) {
        Write-Success "Poppler bereits installiert"
        return $popplerBin
    }

    Write-Info "Lade Poppler fuer Windows herunter..."

    try {
        $popplerApi = "https://api.github.com/repos/oschwartz10612/poppler-windows/releases/latest"
        $release = Invoke-RestMethod -Uri $popplerApi -TimeoutSec 15
        $asset = $release.assets |
                 Where-Object { $_.name -like "*.zip" } |
                 Select-Object -First 1

        if (-not $asset) {
            Stop-Install "Konnte Poppler-Download nicht finden."
        }

        $popplerZip = Join-Path $env:TEMP "poppler.zip"
        $popplerTmp = Join-Path $env:TEMP "poppler-extract"

        Write-Info "Lade herunter: $($asset.name)"
        Invoke-WebRequest -Uri $asset.browser_download_url `
            -OutFile $popplerZip -UseBasicParsing

        Expand-Archive -Path $popplerZip `
            -DestinationPath $popplerTmp -Force

        $extracted = Get-ChildItem $popplerTmp -Directory |
                     Select-Object -First 1
        if ($extracted) {
            New-Item -ItemType Directory -Path $popplerDir `
                -Force | Out-Null
            Copy-Item "$($extracted.FullName)\*" `
                -Destination $popplerDir -Recurse -Force
        }

        Remove-Item $popplerZip -Force -ErrorAction SilentlyContinue
        Remove-Item $popplerTmp -Recurse -Force -ErrorAction SilentlyContinue

        Write-Success "Poppler installiert: $popplerBin"
        return $popplerBin

    } catch {
        Write-Warn "Poppler-Download fehlgeschlagen: $_"
        Write-Info "Bitte manuell installieren:"
        Write-Info "https://github.com/oschwartz10612/poppler-windows/releases"
        Write-Info "Entpacken nach: $popplerDir"
        return $popplerBin
    }
}

# ── Backup user data ───────────────────────────────────────────
function Backup-UserData {
    Write-Header "Sichere Benutzerdaten..."

    New-Item -ItemType Directory -Path $BackupDir `
        -Force | Out-Null

    $backedUp = 0
    $files = @{
        "data\Datenbank.xlsx"      = "Datenbank.xlsx"
        "config\settings.json"     = "settings.json"
        "config\credentials.json"  = "credentials.json"
        "data\discogs_cache.db"    = "discogs_cache.db"
    }

    foreach ($rel in $files.Keys) {
        $src = Join-Path $InstallDir $rel
        $dst = Join-Path $BackupDir $files[$rel]
        if (Test-Path $src) {
            Copy-Item $src $dst -Force
            $backedUp++
        }
    }

    if ($backedUp -gt 0) {
        Write-Success "$backedUp Datei(en) gesichert nach: $BackupDir"
    } else {
        Write-Info "Keine Benutzerdaten zum Sichern gefunden"
    }
}

# ── Restore user data ──────────────────────────────────────────
function Restore-UserData {
    if (-not (Test-Path $BackupDir)) { return }
    Write-Header "Stelle Benutzerdaten wieder her..."

    New-Item -ItemType Directory `
        -Path (Join-Path $InstallDir "data") `
        -Force | Out-Null
    New-Item -ItemType Directory `
        -Path (Join-Path $InstallDir "config") `
        -Force | Out-Null

    $restored = 0
    $files = @{
        "Datenbank.xlsx"   = "data\Datenbank.xlsx"
        "settings.json"    = "config\settings.json"
        "credentials.json" = "config\credentials.json"
        "discogs_cache.db" = "data\discogs_cache.db"
    }

    foreach ($file in $files.Keys) {
        $src = Join-Path $BackupDir $file
        $dst = Join-Path $InstallDir $files[$file]
        if (Test-Path $src) {
            Copy-Item $src $dst -Force
            $restored++
        }
    }

    if ($restored -gt 0) {
        Write-Success "$restored Datei(en) wiederhergestellt"
    }
    Write-Info "Backup bleibt erhalten unter: $BackupDir"
}

# ── Download app ───────────────────────────────────────────────
function Get-App {
    param($Version)
    Write-Header "Lade App herunter..."

    $zipUrl = if ($Version) {
        "$RepoUrl/archive/refs/tags/v$Version.zip"
    } else {
        "$RepoUrl/archive/refs/heads/main.zip"
    }

    Write-Info "URL: $zipUrl"

    $tmpZip = Join-Path $env:TEMP "vinyl-label-printer-$PID.zip"
    $tmpDir = Join-Path $env:TEMP "vinyl-label-printer-$PID"

    try {
        Invoke-WebRequest -Uri $zipUrl `
            -OutFile $tmpZip -UseBasicParsing
    } catch {
        Stop-Install "Download fehlgeschlagen: $_"
    }

    Expand-Archive -Path $tmpZip `
        -DestinationPath $tmpDir -Force

    $extracted = Get-ChildItem $tmpDir -Directory |
                 Select-Object -First 1
    $appSource = Join-Path $extracted.FullName $AppSubDir

    if (-not (Test-Path $appSource)) {
        Stop-Install "App-Verzeichnis nicht gefunden: $appSource"
    }

    New-Item -ItemType Directory -Path $InstallDir `
        -Force | Out-Null
    Copy-Item "$appSource\*" -Destination $InstallDir `
        -Recurse -Force

    Remove-Item $tmpZip -Force -ErrorAction SilentlyContinue
    Remove-Item $tmpDir -Recurse -Force -ErrorAction SilentlyContinue

    Write-Success "App heruntergeladen und entpackt"
}

# ── Setup venv ─────────────────────────────────────────────────
function Initialize-Venv {
    param($PythonCmd)
    Write-Header "Richte Python-Umgebung ein..."

    $venvDir = Join-Path $InstallDir "venv"
    $venvPip = Join-Path $venvDir "Scripts\pip.exe"
    $reqFile = Join-Path $InstallDir "requirements.txt"

    if (-not (Test-Path $venvDir)) {
        & $PythonCmd -m venv $venvDir
        Write-Success "Virtual Environment erstellt"
    } else {
        Write-Info "Virtual Environment bereits vorhanden — aktualisiere..."
    }

    & $venvPip install --upgrade pip -q
    & $venvPip install -r $reqFile --upgrade -q

    Write-Success "Python-Pakete installiert"
}

# ── Patch settings for Poppler path ───────────────────────────
function Set-PopplerPath {
    param($PopplerBin)
    Write-Header "Konfiguriere Poppler-Pfad..."

    $settingsFile = Join-Path $InstallDir "config\settings.json"

    New-Item -ItemType Directory `
        -Path (Join-Path $InstallDir "config") `
        -Force | Out-Null

    if (Test-Path $settingsFile) {
        $settings = Get-Content $settingsFile |
                    ConvertFrom-Json
    } else {
        $settings = [PSCustomObject]@{}
    }

    $settings | Add-Member -NotePropertyName "poppler_path" `
        -NotePropertyValue $PopplerBin -Force

    $settings | ConvertTo-Json -Depth 10 |
        Set-Content $settingsFile -Encoding UTF8

    Write-Success "Poppler-Pfad gespeichert: $PopplerBin"
}

# ── Create start.bat ───────────────────────────────────────────
function New-StartBat {
    Write-Header "Erstelle start.bat..."

    $startBat = Join-Path $InstallDir "start.bat"
    @"
@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
python main.py
echo.
echo === App beendet. Druecke eine Taste zum Schliessen ===
pause
"@ | Set-Content $startBat -Encoding UTF8

    Write-Success "start.bat erstellt: $startBat"
}

# ── Create Start Menu shortcut ─────────────────────────────────
function New-StartMenuShortcut {
    Write-Header "Erstelle Startmenue-Eintrag..."

    $startBat = Join-Path $InstallDir "start.bat"
    $wsh = New-Object -ComObject WScript.Shell
    $shortcut = $wsh.CreateShortcut($ShortcutPath)
    $shortcut.TargetPath = $startBat
    $shortcut.WorkingDirectory = $InstallDir
    $shortcut.Description = "7 Vinyl Labels drucken"
    $shortcut.WindowStyle = 1
    $shortcut.IconLocation = "shell32.dll,17"
    $shortcut.Save()

    Write-Success "Startmenue-Eintrag erstellt"
}

# ── Copy example database ──────────────────────────────────────
function Initialize-Database {
    $dbPath = Join-Path $InstallDir "data\Datenbank.xlsx"

    if (-not (Test-Path $dbPath)) {
        New-Item -ItemType Directory `
            -Path (Join-Path $InstallDir "data") `
            -Force | Out-Null

        $example = Join-Path $InstallDir "examples\database.xlsx"
        if (Test-Path $example) {
            Copy-Item $example $dbPath
            Write-Success "Beispiel-Datenbank erstellt: $dbPath"
        } else {
            Write-Warn "Keine Beispiel-Datenbank gefunden."
            Write-Info "Bitte Datenbank.xlsx manuell kopieren nach:"
            Write-Info "  $dbPath"
        }
    }
}

# ── Uninstall ──────────────────────────────────────────────────
function Remove-App {
    Write-Header "Deinstalliere Vinyl Label Printer..."

    Write-Host ""
    Write-Host "Folgendes wird geloescht:" -ForegroundColor Yellow
    Write-Host "  $InstallDir"
    Write-Host "  $ShortcutPath"
    Write-Host ""
    Write-Host "Benutzerdaten bleiben erhalten." -ForegroundColor Yellow
    Write-Host ""

    $confirm = Read-Host "Wirklich deinstallieren? [j/N]"
    if ($confirm -notmatch "^[jJyY]$") {
        Write-Info "Abgebrochen."
        exit 0
    }

    Backup-UserData

    Remove-Item $InstallDir -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item $ShortcutPath -Force -ErrorAction SilentlyContinue

    Write-Success "Deinstallation abgeschlossen."
    Write-Info "Ihre Daten wurden gesichert nach: $BackupDir"
}

# ── Main ───────────────────────────────────────────────────────
function Main {
    Write-Host ""
    Write-Host "╔══════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║   Vinyl Label Printer — Windows      ║" -ForegroundColor Green
    Write-Host "╚══════════════════════════════════════╝" -ForegroundColor Green
    Write-Host ""

    if ($Uninstall) {
        Remove-App
        return
    }

    $installedVersion = Get-InstalledVersion
    $isUpdate = $installedVersion -ne ""

    if ($isUpdate) {
        Write-Info "Bestehende Installation gefunden: v$installedVersion"
    } else {
        Write-Info "Keine bestehende Installation — Neuinstallation"
    }

    Write-Info "Pruefe verfuegbare Version..."
    $latestVersion = Get-LatestVersion

    if ($latestVersion) {
        Write-Info "Verfuegbare Version: v$latestVersion"
    } else {
        Write-Warn "Version konnte nicht geprueft werden — installiere main branch"
    }

    if ($isUpdate -and $latestVersion -and
        $installedVersion -eq $latestVersion) {
        Write-Host ""
        Write-Success "Bereits aktuell (v$installedVersion) — kein Update noetig."
        Write-Host ""
        Write-Info "Starte die App mit:"
        Write-Info "  $InstallDir\start.bat"
        Write-Info "  oder ueber das Startmenue"
        return
    }

    if ($isUpdate) {
        Write-Host ""
        $msg = if ($latestVersion) {
            "Update: v$installedVersion -> v$latestVersion"
        } else {
            "Update der bestehenden Installation"
        }
        Write-Host $msg -ForegroundColor Yellow
        $confirm = Read-Host "Fortfahren? [J/n]"
        if ($confirm -match "^[nN]$") {
            Write-Info "Abgebrochen."
            return
        }
    }

    $pythonCmd = Test-Python
    if ($isUpdate) { Backup-UserData }
    Get-App -Version $latestVersion
    if ($isUpdate) { Restore-UserData }
    $popplerBin = Install-Poppler
    Initialize-Venv -PythonCmd $pythonCmd
    Set-PopplerPath -PopplerBin $popplerBin
    Initialize-Database
    New-StartBat
    New-StartMenuShortcut

    Write-Host ""
    Write-Host "╔══════════════════════════════════════╗" -ForegroundColor Green
    if ($isUpdate) {
        Write-Host "║   Update erfolgreich abgeschlossen!  ║" -ForegroundColor Green
    } else {
        Write-Host "║   Installation erfolgreich!           ║" -ForegroundColor Green
    }
    Write-Host "╚══════════════════════════════════════╝" -ForegroundColor Green
    Write-Host ""

    if ($isUpdate -and (Test-Path $BackupDir)) {
        Write-Info "Backup Ihrer Daten: $BackupDir"
    }

    Write-Host ""
    Write-Info "App starten:"
    Write-Host "  Doppelklick: $InstallDir\start.bat"
    Write-Host "  oder ueber das Startmenue: 'Vinyl Label Printer'"
    Write-Host ""
    Write-Info "Deinstallieren:"
    Write-Host "  powershell -File install.ps1 -Uninstall"
    Write-Host ""
}

Main

#Requires -Version 5.1
<#
.SYNOPSIS
    Vinyl Label Printer — Install & Update Script for Windows
.DESCRIPTION
    Installs or updates Vinyl Label Printer on Windows 10/11.
    Handles fresh installation and updates automatically.
    User data (database.xlsx, settings, credentials) is
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
        Write-Warn "Could not fetch version from GitHub."
    }
    return ""
}

# ── Check Python ───────────────────────────────────────────────
function Test-Python {
    Write-Header "Checking system requirements..."

    $python = $null
    foreach ($cmd in @("python", "python3", "py")) {
        try {
            $ver = & $cmd --version 2>&1
            if ($ver -match "Python (\d+)\.(\d+)") {
                $major = [int]$Matches[1]
                $minor = [int]$Matches[2]
                if ($major -ge 3 -and $minor -ge 10) {
                    $python = $cmd
                    Write-Success "Python $major.$minor found ($cmd)"
                    break
                } else {
                    Write-Warn "Python $major.$minor too old (3.10+ required)"
                }
            }
        } catch { continue }
    }

    if (-not $python) {
        Write-Err "Python 3.10+ not found."
        Write-Info "Download from: https://www.python.org/downloads/"
        Write-Info "Important: check 'Add Python to PATH' during installation!"
        Start-Process "https://www.python.org/downloads/"
        Stop-Install "Python 3.10+ is required."
    }

    return $python
}

# ── Check/Install Poppler ──────────────────────────────────────
function Install-Poppler {
    Write-Header "Checking Poppler (PDF preview)..."

    $popplerDir = Join-Path $InstallDir "poppler"
    $popplerBin = Join-Path $popplerDir "Library\bin"

    if (Test-Path (Join-Path $popplerBin "pdftoppm.exe")) {
        Write-Success "Poppler already installed"
        return $popplerBin
    }

    Write-Info "Downloading Poppler for Windows..."

    try {
        $popplerApi = "https://api.github.com/repos/oschwartz10612/poppler-windows/releases/latest"
        $release = Invoke-RestMethod -Uri $popplerApi -TimeoutSec 15
        $asset = $release.assets |
                 Where-Object { $_.name -like "*.zip" } |
                 Select-Object -First 1

        if (-not $asset) {
            Stop-Install "Could not find Poppler download asset."
        }

        $popplerZip = Join-Path $env:TEMP "poppler.zip"
        $popplerTmp = Join-Path $env:TEMP "poppler-extract"

        Write-Info "Downloading: $($asset.name)"
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

        Write-Success "Poppler installed: $popplerBin"
        return $popplerBin

    } catch {
        Write-Warn "Poppler download failed: $_"
        Write-Info "Please install manually:"
        Write-Info "https://github.com/oschwartz10612/poppler-windows/releases"
        Write-Info "Extract to: $popplerDir"
        return $popplerBin
    }
}

# ── Backup user data ───────────────────────────────────────────
function Backup-UserData {
    Write-Header "Backing up user data..."

    New-Item -ItemType Directory -Path $BackupDir `
        -Force | Out-Null

    $backedUp = 0
    $files = @{
        "data\database.xlsx"       = "database.xlsx"
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
        Write-Success "$backedUp file(s) backed up to: $BackupDir"
    } else {
        Write-Info "No user data found to back up"
    }
}

# ── Restore user data ──────────────────────────────────────────
function Restore-UserData {
    if (-not (Test-Path $BackupDir)) { return }
    Write-Header "Restoring user data..."

    New-Item -ItemType Directory `
        -Path (Join-Path $InstallDir "data") `
        -Force | Out-Null
    New-Item -ItemType Directory `
        -Path (Join-Path $InstallDir "config") `
        -Force | Out-Null

    $restored = 0
    $files = @{
        "database.xlsx"    = "data\database.xlsx"
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
        Write-Success "$restored file(s) restored"
    }
    Write-Info "Backup kept at: $BackupDir"
}

# ── Download app ───────────────────────────────────────────────
function Get-App {
    param($Version)
    Write-Header "Downloading app..."

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
        Stop-Install "Download failed: $_"
    }

    Expand-Archive -Path $tmpZip `
        -DestinationPath $tmpDir -Force

    $extracted = Get-ChildItem $tmpDir -Directory |
                 Select-Object -First 1
    $appSource = Join-Path $extracted.FullName $AppSubDir

    if (-not (Test-Path $appSource)) {
        Stop-Install "App directory not found: $appSource"
    }

    New-Item -ItemType Directory -Path $InstallDir `
        -Force | Out-Null
    Copy-Item "$appSource\*" -Destination $InstallDir `
        -Recurse -Force

    # Copy examples/ alongside app (used for first-run database setup)
    $examplesSource = Join-Path $extracted.FullName "examples"
    if (Test-Path $examplesSource) {
        Copy-Item $examplesSource `
            -Destination (Join-Path $InstallDir "examples") `
            -Recurse -Force
    }

    Remove-Item $tmpZip -Force -ErrorAction SilentlyContinue
    Remove-Item $tmpDir -Recurse -Force -ErrorAction SilentlyContinue

    Write-Success "App downloaded and extracted"
}

# ── Setup venv ─────────────────────────────────────────────────
function Initialize-Venv {
    param($PythonCmd)
    Write-Header "Setting up Python environment..."

    $venvDir = Join-Path $InstallDir "venv"
    $venvPip = Join-Path $venvDir "Scripts\pip.exe"
    $reqFile = Join-Path $InstallDir "requirements.txt"

    if (-not (Test-Path $venvDir)) {
        & $PythonCmd -m venv $venvDir
        Write-Success "Virtual environment created"
    } else {
        Write-Info "Virtual environment already exists — updating..."
    }

    & $venvPip install --upgrade pip -q
    & $venvPip install -r $reqFile --upgrade -q

    Write-Success "Python packages installed"
}

# ── Patch settings for Poppler path ───────────────────────────
function Set-PopplerPath {
    param($PopplerBin)
    Write-Header "Configuring Poppler path..."

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

    Write-Success "Poppler path saved: $PopplerBin"
}

# ── Create start.bat ───────────────────────────────────────────
function New-StartBat {
    Write-Header "Creating start.bat..."

    $startBat = Join-Path $InstallDir "start.bat"
    @"
@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
python main.py
echo.
echo === App closed. Press any key to exit ===
pause
"@ | Set-Content $startBat -Encoding UTF8

    Write-Success "start.bat created: $startBat"
}

# ── Create Start Menu shortcut ─────────────────────────────────
function New-StartMenuShortcut {
    Write-Header "Creating Start Menu shortcut..."

    $startBat = Join-Path $InstallDir "start.bat"
    $wsh = New-Object -ComObject WScript.Shell
    $shortcut = $wsh.CreateShortcut($ShortcutPath)
    $shortcut.TargetPath = $startBat
    $shortcut.WorkingDirectory = $InstallDir
    $shortcut.Description = "Print 7-inch vinyl labels"
    $shortcut.WindowStyle = 1
    $shortcut.IconLocation = "shell32.dll,17"
    $shortcut.Save()

    Write-Success "Start Menu shortcut created"
}

# ── Copy example database ──────────────────────────────────────
function Initialize-Database {
    $dbPath = Join-Path $InstallDir "data\database.xlsx"

    if (-not (Test-Path $dbPath)) {
        New-Item -ItemType Directory `
            -Path (Join-Path $InstallDir "data") `
            -Force | Out-Null

        $example = Join-Path $InstallDir "examples\database.xlsx"
        if (Test-Path $example) {
            Copy-Item $example $dbPath
            Write-Success "Example database copied to: $dbPath"
        } else {
            Write-Warn "Example database not found."
            Write-Warn "Please copy the file manually:"
            Write-Warn "  Source: examples\database.xlsx (GitHub repository)"
            Write-Warn "  Target: $dbPath"
            Write-Info "Download: https://github.com/EJAIS/vinylsticker/raw/main/examples/database.xlsx"
        }
    }
}

# ── Uninstall ──────────────────────────────────────────────────
function Remove-App {
    Write-Header "Uninstalling Vinyl Label Printer..."

    Write-Host ""
    Write-Host "The following will be deleted:" -ForegroundColor Yellow
    Write-Host "  $InstallDir"
    Write-Host "  $ShortcutPath"
    Write-Host ""
    Write-Host "User data will be preserved." -ForegroundColor Yellow
    Write-Host ""

    $confirm = Read-Host "Really uninstall? [y/N]"
    if ($confirm -notmatch "^[yYjJ]$") {
        Write-Info "Cancelled."
        exit 0
    }

    Backup-UserData

    Remove-Item $InstallDir -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item $ShortcutPath -Force -ErrorAction SilentlyContinue

    Write-Success "Uninstall complete."
    Write-Info "Your data was backed up to: $BackupDir"
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
        Write-Info "Existing installation found: v$installedVersion"
    } else {
        Write-Info "No existing installation found — fresh install"
    }

    Write-Info "Checking available version..."
    $latestVersion = Get-LatestVersion

    if ($latestVersion) {
        Write-Info "Available version: v$latestVersion"
    } else {
        Write-Warn "Could not check version — installing main branch"
    }

    if ($isUpdate -and $latestVersion -and
        $installedVersion -eq $latestVersion) {
        Write-Host ""
        Write-Success "Already up to date (v$installedVersion) — no update needed."
        Write-Host ""
        Write-Info "Start the app:"
        Write-Info "  $InstallDir\start.bat"
        Write-Info "  or via Start Menu"
        return
    }

    if ($isUpdate) {
        Write-Host ""
        $msg = if ($latestVersion) {
            "Update: v$installedVersion -> v$latestVersion"
        } else {
            "Update existing installation"
        }
        Write-Host $msg -ForegroundColor Yellow
        $confirm = Read-Host "Continue? [Y/n]"
        if ($confirm -match "^[nN]$") {
            Write-Info "Cancelled."
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
        Write-Host "║         Update complete!             ║" -ForegroundColor Green
    } else {
        Write-Host "║   Installation complete! Enjoy!      ║" -ForegroundColor Green
    }
    Write-Host "╚══════════════════════════════════════╝" -ForegroundColor Green
    Write-Host ""

    if ($isUpdate -and (Test-Path $BackupDir)) {
        Write-Info "Data backup location: $BackupDir"
    }

    Write-Host ""
    Write-Info "Start the app:"
    Write-Host "  Double-click: $InstallDir\start.bat"
    Write-Host "  or via Start Menu: 'Vinyl Label Printer'"
    Write-Host ""
    Write-Info "Uninstall (if install.ps1 is local):"
    Write-Host "  powershell -ExecutionPolicy Bypass -File install.ps1 -Uninstall"
    Write-Host ""
    Write-Info "Uninstall (via web):"
    Write-Host "  Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/EJAIS/vinylsticker/main/install.ps1' -OutFile `"`$env:TEMP\install.ps1`"; powershell -ExecutionPolicy Bypass -File `"`$env:TEMP\install.ps1`" -Uninstall"
    Write-Host ""
}

Main

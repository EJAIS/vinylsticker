#!/bin/bash
# =============================================================
# Vinyl Label Printer — Install & Update Script
# https://github.com/EJAIS/vinylsticker
# =============================================================
# Usage:
#   curl -sSL https://raw.githubusercontent.com/EJAIS/vinylsticker/main/install.sh | bash
#   or: bash install.sh
# =============================================================

set -euo pipefail

# ── Configuration ─────────────────────────────────────────────
REPO_OWNER="EJAIS"
REPO_NAME="vinylsticker"
REPO_URL="https://github.com/${REPO_OWNER}/${REPO_NAME}"
REPO_API="https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}"
INSTALL_DIR="$HOME/vinyl-label-printer"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
BACKUP_DIR="/tmp/vinyl-label-printer-backup-$(date +%Y%m%d_%H%M%S)"
APP_SUBDIR="vinyl-label-printer"   # subfolder inside the repo

# ── Colors ────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# ── Helper functions ──────────────────────────────────────────
info()    { echo -e "${BLUE}ℹ${NC}  $*"; }
success() { echo -e "${GREEN}✓${NC}  $*"; }
warning() { echo -e "${YELLOW}⚠${NC}  $*"; }
error()   { echo -e "${RED}✗${NC}  $*" >&2; }
header()  { echo -e "\n${BOLD}$*${NC}"; }
die()     { error "$*"; exit 1; }

# ── Version helpers ───────────────────────────────────────────
get_installed_version() {
    local ver_file="$INSTALL_DIR/__version__.py"
    if [ -f "$ver_file" ]; then
        grep '__version__' "$ver_file" \
            | head -1 \
            | sed 's/.*"\(.*\)".*/\1/'
    else
        echo ""
    fi
}

get_latest_version() {
    curl -sf \
        -H "Accept: application/vnd.github+json" \
        "${REPO_API}/releases" \
    | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data:
        print(data[0]['tag_name'].lstrip('v'))
    else:
        print('')
except Exception:
    print('')
" 2>/dev/null || echo ""
}

# ── Dependency check ──────────────────────────────────────────
check_dependencies() {
    header "🔍 Prüfe Systemvoraussetzungen..."

    # Python 3.10+
    if ! command -v python3 &>/dev/null; then
        die "Python 3 nicht gefunden. Bitte installieren: sudo apt install python3"
    fi

    PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
    PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)

    if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
        die "Python 3.10+ erforderlich (gefunden: $PY_VERSION)"
    fi
    success "Python $PY_VERSION ✓"

    # curl
    if ! command -v curl &>/dev/null; then
        die "curl nicht gefunden. Bitte installieren: sudo apt install curl"
    fi
    success "curl ✓"

    # unzip
    if ! command -v unzip &>/dev/null; then
        die "unzip nicht gefunden. Bitte installieren: sudo apt install unzip"
    fi
    success "unzip ✓"
}

# ── System packages ───────────────────────────────────────────
install_system_packages() {
    header "📦 Installiere System-Pakete..."

    local packages=(
        "python3-venv"
        "python3-pip"
        "poppler-utils"
        "libxcb-cursor0"
        "libxcb-icccm4"
        "libxcb-image0"
        "libxcb-keysyms1"
        "libxcb-randr0"
        "libxcb-render-util0"
        "libxcb-xinerama0"
        "libxcb-xkb1"
        "libxkbcommon-x11-0"
    )

    local missing=()
    for pkg in "${packages[@]}"; do
        if ! dpkg -l "$pkg" &>/dev/null; then
            missing+=("$pkg")
        fi
    done

    if [ ${#missing[@]} -eq 0 ]; then
        success "Alle System-Pakete bereits installiert"
        return
    fi

    info "Folgende Pakete werden installiert: ${missing[*]}"
    sudo apt-get update -qq
    sudo apt-get install -y -qq "${missing[@]}"
    success "System-Pakete installiert"
}

# ── Backup user data ──────────────────────────────────────────
backup_user_data() {
    header "💾 Sichere Benutzerdaten..."

    mkdir -p "$BACKUP_DIR"

    local backed_up=0

    # Datenbank.xlsx
    if [ -f "$INSTALL_DIR/data/Datenbank.xlsx" ]; then
        cp "$INSTALL_DIR/data/Datenbank.xlsx" \
           "$BACKUP_DIR/Datenbank.xlsx"
        backed_up=$((backed_up + 1))
    fi

    # settings.json
    if [ -f "$INSTALL_DIR/config/settings.json" ]; then
        cp "$INSTALL_DIR/config/settings.json" \
           "$BACKUP_DIR/settings.json"
        backed_up=$((backed_up + 1))
    fi

    # credentials.json
    if [ -f "$INSTALL_DIR/config/credentials.json" ]; then
        cp "$INSTALL_DIR/config/credentials.json" \
           "$BACKUP_DIR/credentials.json"
        backed_up=$((backed_up + 1))
    fi

    # discogs_cache.db (optional — large file)
    if [ -f "$INSTALL_DIR/data/discogs_cache.db" ]; then
        cp "$INSTALL_DIR/data/discogs_cache.db" \
           "$BACKUP_DIR/discogs_cache.db"
        backed_up=$((backed_up + 1))
    fi

    if [ $backed_up -gt 0 ]; then
        success "$backed_up Datei(en) gesichert nach: $BACKUP_DIR"
    else
        info "Keine Benutzerdaten zum Sichern gefunden"
    fi
}

# ── Restore user data ─────────────────────────────────────────
restore_user_data() {
    if [ ! -d "$BACKUP_DIR" ]; then
        return
    fi

    header "♻️  Stelle Benutzerdaten wieder her..."

    mkdir -p "$INSTALL_DIR/data"
    mkdir -p "$INSTALL_DIR/config"

    local restored=0

    if [ -f "$BACKUP_DIR/Datenbank.xlsx" ]; then
        cp "$BACKUP_DIR/Datenbank.xlsx" \
           "$INSTALL_DIR/data/Datenbank.xlsx"
        restored=$((restored + 1))
    fi

    if [ -f "$BACKUP_DIR/settings.json" ]; then
        cp "$BACKUP_DIR/settings.json" \
           "$INSTALL_DIR/config/settings.json"
        restored=$((restored + 1))
    fi

    if [ -f "$BACKUP_DIR/credentials.json" ]; then
        cp "$BACKUP_DIR/credentials.json" \
           "$INSTALL_DIR/config/credentials.json"
        chmod 600 "$INSTALL_DIR/config/credentials.json"
        restored=$((restored + 1))
    fi

    if [ -f "$BACKUP_DIR/discogs_cache.db" ]; then
        cp "$BACKUP_DIR/discogs_cache.db" \
           "$INSTALL_DIR/data/discogs_cache.db"
        restored=$((restored + 1))
    fi

    if [ $restored -gt 0 ]; then
        success "$restored Datei(en) wiederhergestellt"
    fi

    # Keep backup for safety — inform user
    info "Backup bleibt erhalten unter: $BACKUP_DIR"
}

# ── Download app ──────────────────────────────────────────────
download_app() {
    local version="$1"
    local zip_url

    if [ -n "$version" ]; then
        zip_url="${REPO_URL}/archive/refs/tags/v${version}.zip"
    else
        zip_url="${REPO_URL}/archive/refs/heads/main.zip"
    fi

    header "⬇️  Lade App herunter..."
    info "URL: $zip_url"

    local tmp_zip="/tmp/vinyl-label-printer-$$.zip"
    local tmp_dir="/tmp/vinyl-label-printer-$$"

    curl -L --progress-bar "$zip_url" -o "$tmp_zip" \
        || die "Download fehlgeschlagen"

    mkdir -p "$tmp_dir"
    unzip -q "$tmp_zip" -d "$tmp_dir" \
        || die "Entpacken fehlgeschlagen"

    # Find extracted folder (name varies by branch/tag)
    local extracted
    extracted=$(find "$tmp_dir" -maxdepth 1 -mindepth 1 \
        -type d | head -1)

    [ -d "$extracted/$APP_SUBDIR" ] \
        || die "App-Verzeichnis nicht gefunden in: $extracted"

    # Install to INSTALL_DIR
    mkdir -p "$INSTALL_DIR"
    cp -r "$extracted/$APP_SUBDIR/." "$INSTALL_DIR/"

    # Cleanup
    rm -f "$tmp_zip"
    rm -rf "$tmp_dir"

    success "App heruntergeladen und entpackt"
}

# ── Setup Python venv ─────────────────────────────────────────
setup_venv() {
    header "🐍 Richte Python-Umgebung ein..."

    if [ ! -d "$INSTALL_DIR/venv" ]; then
        python3 -m venv "$INSTALL_DIR/venv"
        success "Virtual Environment erstellt"
    else
        info "Virtual Environment bereits vorhanden — aktualisiere..."
    fi

    "$INSTALL_DIR/venv/bin/pip" install --upgrade pip -q
    "$INSTALL_DIR/venv/bin/pip" install \
        -r "$INSTALL_DIR/requirements.txt" \
        --upgrade -q

    success "Python-Pakete installiert"
}

# ── Create launcher ───────────────────────────────────────────
create_launcher() {
    header "🚀 Erstelle Starter..."

    mkdir -p "$BIN_DIR"

    cat > "$BIN_DIR/vinyl-label-printer" << EOF
#!/bin/bash
# Vinyl Label Printer — Launcher
cd "$INSTALL_DIR"
source venv/bin/activate
exec python3 main.py "\$@"
EOF
    chmod +x "$BIN_DIR/vinyl-label-printer"
    success "Starter erstellt: $BIN_DIR/vinyl-label-printer"

    # Add ~/.local/bin to PATH if not already there
    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        warning "~/.local/bin ist nicht im PATH."
        info "Füge folgende Zeile zu ~/.bashrc hinzu:"
        info '  export PATH="$HOME/.local/bin:$PATH"'
        info "Oder starte die App mit: ~/vinyl-label-printer/start.sh"
    fi
}

# ── Create start.sh ───────────────────────────────────────────
create_start_sh() {
    cat > "$INSTALL_DIR/start.sh" << EOF
#!/bin/bash
cd "\$(dirname "\$0")"
source venv/bin/activate
python3 main.py "\$@"
echo ""
echo "=== App beendet. Drücke Enter zum Schließen ==="
read
EOF
    chmod +x "$INSTALL_DIR/start.sh"
    success "start.sh erstellt: $INSTALL_DIR/start.sh"
}

# ── Create desktop entry ──────────────────────────────────────
create_desktop_entry() {
    header "🖥️  Erstelle Menü-Eintrag..."

    mkdir -p "$DESKTOP_DIR"

    cat > "$DESKTOP_DIR/vinyl-label-printer.desktop" << EOF
[Desktop Entry]
Name=Vinyl Label Printer
GenericName=Vinyl Label Printer
Comment=7" Vinyl Labels auf Avery 4780 drucken
Exec=$BIN_DIR/vinyl-label-printer
Icon=printer
Terminal=false
Type=Application
Categories=Utility;Office;
Keywords=vinyl;label;druck;avery;discogs;
StartupNotify=true
EOF

    # Refresh desktop database
    if command -v update-desktop-database &>/dev/null; then
        update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
    fi

    success "Menü-Eintrag erstellt"
}

# ── Copy example database ─────────────────────────────────────
setup_example_database() {
    local db_path="$INSTALL_DIR/data/Datenbank.xlsx"

    if [ ! -f "$db_path" ]; then
        mkdir -p "$INSTALL_DIR/data"
        local example="$INSTALL_DIR/examples/database.xlsx"
        if [ -f "$example" ]; then
            cp "$example" "$db_path"
            success "Beispiel-Datenbank erstellt: $db_path"
        else
            warning "Keine Beispiel-Datenbank gefunden."
            info "Bitte Datenbank.xlsx manuell nach $db_path kopieren."
        fi
    fi
}

# ── Uninstall ─────────────────────────────────────────────────
uninstall() {
    header "🗑️  Deinstalliere Vinyl Label Printer..."

    echo -e "${YELLOW}Folgendes wird gelöscht:${NC}"
    echo "  $INSTALL_DIR"
    echo "  $BIN_DIR/vinyl-label-printer"
    echo "  $DESKTOP_DIR/vinyl-label-printer.desktop"
    echo ""
    echo -e "${YELLOW}Benutzerdaten (Datenbank, Einstellungen) bleiben erhalten.${NC}"
    echo ""
    read -rp "Wirklich deinstallieren? [j/N] " confirm
    [[ "$confirm" =~ ^[jJyY]$ ]] || { info "Abgebrochen."; exit 0; }

    # Backup user data before uninstall
    backup_user_data

    rm -rf "$INSTALL_DIR"
    rm -f "$BIN_DIR/vinyl-label-printer"
    rm -f "$DESKTOP_DIR/vinyl-label-printer.desktop"

    success "Deinstallation abgeschlossen."
    info "Ihre Daten wurden gesichert nach: $BACKUP_DIR"
}

# ── Main ──────────────────────────────────────────────────────
main() {
    echo ""
    echo -e "${BOLD}╔════════════════════════════════════╗${NC}"
    echo -e "${BOLD}║    Vinyl Label Printer Installer   ║${NC}"
    echo -e "${BOLD}╚════════════════════════════════════╝${NC}"
    echo ""

    # Handle --uninstall flag
    if [[ "${1:-}" == "--uninstall" ]]; then
        uninstall
        exit 0
    fi

    # Detect fresh install vs. update
    INSTALLED_VERSION=$(get_installed_version)
    IS_UPDATE=false

    if [ -n "$INSTALLED_VERSION" ]; then
        IS_UPDATE=true
        info "Bestehende Installation gefunden: v$INSTALLED_VERSION"
    else
        info "Keine bestehende Installation gefunden — Neuinstallation"
    fi

    # Get latest available version
    info "Prüfe verfügbare Version..."
    LATEST_VERSION=$(get_latest_version)

    if [ -n "$LATEST_VERSION" ]; then
        info "Verfügbare Version: v$LATEST_VERSION"
    else
        warning "Konnte Version nicht von GitHub abrufen — installiere main branch"
    fi

    # Skip update if already up to date
    if [ "$IS_UPDATE" = true ] && \
       [ -n "$LATEST_VERSION" ] && \
       [ "$INSTALLED_VERSION" = "$LATEST_VERSION" ]; then
        echo ""
        success "Bereits aktuell (v$INSTALLED_VERSION) — kein Update nötig."
        echo ""
        info "Starte die App mit: vinyl-label-printer"
        info "oder:               $INSTALL_DIR/start.sh"
        exit 0
    fi

    # Confirm update
    if [ "$IS_UPDATE" = true ]; then
        echo ""
        if [ -n "$LATEST_VERSION" ]; then
            echo -e "${YELLOW}Update: v$INSTALLED_VERSION → v$LATEST_VERSION${NC}"
        else
            echo -e "${YELLOW}Update der bestehenden Installation${NC}"
        fi
        read -rp "Fortfahren? [J/n] " confirm
        confirm="${confirm:-J}"
        [[ "$confirm" =~ ^[jJyY]$ ]] || { info "Abgebrochen."; exit 0; }
    fi

    # Run installation / update steps
    check_dependencies
    install_system_packages

    if [ "$IS_UPDATE" = true ]; then
        backup_user_data
    fi

    download_app "$LATEST_VERSION"

    if [ "$IS_UPDATE" = true ]; then
        restore_user_data
    fi

    setup_venv
    setup_example_database
    create_launcher
    create_start_sh
    create_desktop_entry

    # Final message
    echo ""
    echo -e "${BOLD}${GREEN}╔════════════════════════════════════╗${NC}"
    if [ "$IS_UPDATE" = true ]; then
        echo -e "${BOLD}${GREEN}║   Update erfolgreich abgeschlossen! ║${NC}"
    else
        echo -e "${BOLD}${GREEN}║  Installation erfolgreich! Viel Spaß ║${NC}"
    fi
    echo -e "${BOLD}${GREEN}╚════════════════════════════════════╝${NC}"
    echo ""

    if [ "$IS_UPDATE" = true ] && [ -d "$BACKUP_DIR" ]; then
        info "Backup Ihrer Daten: $BACKUP_DIR"
    fi

    echo ""
    info "App starten:"
    echo "   vinyl-label-printer    (falls ~/.local/bin im PATH)"
    echo "   $INSTALL_DIR/start.sh"
    echo "   oder über das Anwendungsmenü"
    echo ""
    info "Deinstallieren:"
    echo "   bash install.sh --uninstall"
    echo ""
}

main "$@"

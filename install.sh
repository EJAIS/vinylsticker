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
warning() { echo -e "${YELLOW}⚠${NC}  $*" >&2; }
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
    header "🔍 Checking system requirements..."

    # Python 3.10+
    if ! command -v python3 &>/dev/null; then
        die "Python 3 not found. Install with: sudo apt install python3"
    fi

    PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
    PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)

    if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
        die "Python 3.10+ required (found: $PY_VERSION)"
    fi
    success "Python $PY_VERSION ✓"

    # curl
    if ! command -v curl &>/dev/null; then
        die "curl not found. Install with: sudo apt install curl"
    fi
    success "curl ✓"

    # unzip
    if ! command -v unzip &>/dev/null; then
        die "unzip not found. Install with: sudo apt install unzip"
    fi
    success "unzip ✓"
}

# ── System packages ───────────────────────────────────────────
install_system_packages() {
    header "📦 Installing system packages..."

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
        success "All system packages already installed"
        return
    fi

    info "Installing packages: ${missing[*]}"
    sudo apt-get update -qq
    sudo apt-get install -y -qq "${missing[@]}"
    success "System packages installed"
}

# ── Backup user data ──────────────────────────────────────────
backup_user_data() {
    header "💾 Backing up user data..."

    mkdir -p "$BACKUP_DIR"

    local backed_up=0

    if [ -f "$INSTALL_DIR/data/database.xlsx" ]; then
        cp "$INSTALL_DIR/data/database.xlsx" \
           "$BACKUP_DIR/database.xlsx"
        backed_up=$((backed_up + 1))
    fi

    if [ -f "$INSTALL_DIR/config/settings.json" ]; then
        cp "$INSTALL_DIR/config/settings.json" \
           "$BACKUP_DIR/settings.json"
        backed_up=$((backed_up + 1))
    fi

    if [ -f "$INSTALL_DIR/config/credentials.json" ]; then
        cp "$INSTALL_DIR/config/credentials.json" \
           "$BACKUP_DIR/credentials.json"
        backed_up=$((backed_up + 1))
    fi

    if [ -f "$INSTALL_DIR/data/discogs_cache.db" ]; then
        cp "$INSTALL_DIR/data/discogs_cache.db" \
           "$BACKUP_DIR/discogs_cache.db"
        backed_up=$((backed_up + 1))
    fi

    if [ $backed_up -gt 0 ]; then
        success "$backed_up file(s) backed up to: $BACKUP_DIR"
    else
        info "No user data found to back up"
    fi
}

# ── Restore user data ─────────────────────────────────────────
restore_user_data() {
    if [ ! -d "$BACKUP_DIR" ]; then
        return
    fi

    header "♻️  Restoring user data..."

    mkdir -p "$INSTALL_DIR/data"
    mkdir -p "$INSTALL_DIR/config"

    local restored=0

    if [ -f "$BACKUP_DIR/database.xlsx" ]; then
        cp "$BACKUP_DIR/database.xlsx" \
           "$INSTALL_DIR/data/database.xlsx"
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
        success "$restored file(s) restored"
    fi

    info "Backup kept at: $BACKUP_DIR"
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

    header "⬇️  Downloading app..."
    info "URL: $zip_url"

    local tmp_zip="/tmp/vinyl-label-printer-$$.zip"
    local tmp_dir="/tmp/vinyl-label-printer-$$"

    curl -L --progress-bar "$zip_url" -o "$tmp_zip" \
        || die "Download failed"

    mkdir -p "$tmp_dir"
    unzip -q "$tmp_zip" -d "$tmp_dir" \
        || die "Extraction failed"

    # Find extracted folder (name varies by branch/tag)
    local extracted
    extracted=$(find "$tmp_dir" -maxdepth 1 -mindepth 1 \
        -type d | head -1)

    [ -d "$extracted/$APP_SUBDIR" ] \
        || die "App directory not found in: $extracted"

    # Install app code
    mkdir -p "$INSTALL_DIR"
    cp -r "$extracted/$APP_SUBDIR/." "$INSTALL_DIR/"

    # Copy examples/ alongside app (used for first-run database setup)
    if [ -d "$extracted/examples" ]; then
        cp -r "$extracted/examples" "$INSTALL_DIR/examples"
    fi

    # Cleanup
    rm -f "$tmp_zip"
    rm -rf "$tmp_dir"

    success "App downloaded and extracted"
}

# ── Setup Python venv ─────────────────────────────────────────
setup_venv() {
    header "🐍 Setting up Python environment..."

    if [ ! -d "$INSTALL_DIR/venv" ]; then
        python3 -m venv "$INSTALL_DIR/venv"
        success "Virtual environment created"
    else
        info "Virtual environment already exists — updating..."
    fi

    "$INSTALL_DIR/venv/bin/pip" install --upgrade pip -q
    "$INSTALL_DIR/venv/bin/pip" install \
        -r "$INSTALL_DIR/requirements.txt" \
        --upgrade -q

    success "Python packages installed"
}

# ── Create launcher ───────────────────────────────────────────
create_launcher() {
    header "🚀 Creating launcher..."

    mkdir -p "$BIN_DIR"

    cat > "$BIN_DIR/vinyl-label-printer" << EOF
#!/bin/bash
# Vinyl Label Printer — Launcher
cd "$INSTALL_DIR"
source venv/bin/activate
exec python3 main.py "\$@"
EOF
    chmod +x "$BIN_DIR/vinyl-label-printer"
    success "Launcher created: $BIN_DIR/vinyl-label-printer"

    # Add ~/.local/bin to PATH if not already there
    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        warning "~/.local/bin is not in PATH."
        info "Add this line to ~/.bashrc:"
        info '  export PATH="$HOME/.local/bin:$PATH"'
        info "Or start the app with: $INSTALL_DIR/start.sh"
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
echo "=== App closed. Press Enter to exit ==="
read
EOF
    chmod +x "$INSTALL_DIR/start.sh"
    success "start.sh created: $INSTALL_DIR/start.sh"
}

# ── Create desktop entry ──────────────────────────────────────
create_desktop_entry() {
    header "🖥️  Creating menu entry..."

    mkdir -p "$DESKTOP_DIR"

    cat > "$DESKTOP_DIR/vinyl-label-printer.desktop" << EOF
[Desktop Entry]
Name=Vinyl Label Printer
GenericName=Vinyl Label Printer
Comment=Print 7" vinyl labels on Avery 4780
Exec=$BIN_DIR/vinyl-label-printer
Icon=printer
Terminal=false
Type=Application
Categories=Utility;Office;
Keywords=vinyl;label;print;avery;discogs;
StartupNotify=true
EOF

    # Refresh desktop database
    if command -v update-desktop-database &>/dev/null; then
        update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
    fi

    success "Menu entry created"
}

# ── Copy example database ─────────────────────────────────────
setup_example_database() {
    local db_path="$INSTALL_DIR/data/database.xlsx"

    if [ ! -f "$db_path" ]; then
        mkdir -p "$INSTALL_DIR/data"
        local example="$INSTALL_DIR/examples/database.xlsx"
        if [ -f "$example" ]; then
            cp "$example" "$db_path"
            success "Example database copied to: $db_path"
        else
            warning "Example database not found."
            warning "Please copy the file manually:"
            warning "  Source: examples/database.xlsx (GitHub repository)"
            warning "  Target: $db_path"
            info "Download: https://github.com/EJAIS/vinylsticker/raw/main/examples/database.xlsx"
        fi
    fi
}

# ── Uninstall ─────────────────────────────────────────────────
uninstall() {
    header "🗑️  Uninstalling Vinyl Label Printer..."

    echo -e "${YELLOW}The following will be deleted:${NC}"
    echo "  $INSTALL_DIR"
    echo "  $BIN_DIR/vinyl-label-printer"
    echo "  $DESKTOP_DIR/vinyl-label-printer.desktop"
    echo ""
    echo -e "${YELLOW}User data (database, settings) will be preserved.${NC}"
    echo ""
    if [ ! -t 0 ]; then
        error "Uninstall cannot run non-interactively."
        error "Please download the script first:"
        error "  curl -sSL https://raw.githubusercontent.com/EJAIS/vinylsticker/main/install.sh -o /tmp/install.sh"
        error "  bash /tmp/install.sh --uninstall"
        exit 1
    fi
    read -rp "Really uninstall? [y/N] " confirm
    [[ "$confirm" =~ ^[yYjJ]$ ]] || { info "Cancelled."; exit 0; }

    # Backup user data before uninstall
    backup_user_data

    rm -rf "$INSTALL_DIR"
    rm -f "$BIN_DIR/vinyl-label-printer"
    rm -f "$DESKTOP_DIR/vinyl-label-printer.desktop"

    success "Uninstall complete."
    info "Your data was backed up to: $BACKUP_DIR"
}

# ── Main ──────────────────────────────────────────────────────
main() {
    echo ""
    echo -e "${BOLD}╔════════════════════════════════════╗${NC}"
    echo -e "${BOLD}║    Vinyl Label Printer Installer   ║${NC}"
    echo -e "${BOLD}╚════════════════════════════════════╝${NC}"
    echo ""

    # Detect if running interactively or via pipe (curl | bash)
    IS_PIPE=false
    if [ ! -t 0 ]; then
        IS_PIPE=true
    fi

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
        info "Existing installation found: v$INSTALLED_VERSION"
    else
        info "No existing installation found — fresh install"
    fi

    # Get latest available version
    info "Checking available version..."
    LATEST_VERSION=$(get_latest_version)

    if [ -n "$LATEST_VERSION" ]; then
        info "Available version: v$LATEST_VERSION"
    else
        warning "Could not fetch version from GitHub — installing main branch"
    fi

    # Skip update if already up to date
    if [ "$IS_UPDATE" = true ] && \
       [ -n "$LATEST_VERSION" ] && \
       [ "$INSTALLED_VERSION" = "$LATEST_VERSION" ]; then
        echo ""
        success "Already up to date (v$INSTALLED_VERSION) — nothing to do."
        if [ "$IS_PIPE" = false ]; then
            echo ""
            info "Start the app:"
            echo "   vinyl-label-printer"
            echo "   $INSTALL_DIR/start.sh"
        fi
        exit 0
    fi

    # Confirm update
    if [ "$IS_UPDATE" = true ]; then
        echo ""
        if [ -n "$LATEST_VERSION" ]; then
            echo -e "${YELLOW}Update: v$INSTALLED_VERSION → v$LATEST_VERSION${NC}"
        else
            echo -e "${YELLOW}Updating existing installation${NC}"
        fi

        if [ "$IS_PIPE" = true ]; then
            info "Running non-interactively — update will proceed automatically."
            info "Run 'bash install.sh --uninstall' to remove the app."
        else
            read -rp "Continue? [Y/n] " confirm
            confirm="${confirm:-Y}"
            if [[ "$confirm" =~ ^[nN]$ ]]; then
                info "Cancelled."
                exit 0
            fi
        fi
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
        echo -e "${BOLD}${GREEN}║       Update complete!             ║${NC}"
    else
        echo -e "${BOLD}${GREEN}║   Installation complete! Enjoy!    ║${NC}"
    fi
    echo -e "${BOLD}${GREEN}╚════════════════════════════════════╝${NC}"
    echo ""

    if [ "$IS_UPDATE" = true ] && [ -d "$BACKUP_DIR" ]; then
        info "Data backup location: $BACKUP_DIR"
    fi

    echo ""
    info "Start the app:"
    echo "   vinyl-label-printer    (if ~/.local/bin is in PATH)"
    echo "   $INSTALL_DIR/start.sh"
    echo "   or via the application menu"
    echo ""
    info "Uninstall (if install.sh is local):"
    echo "   bash install.sh --uninstall"
    echo ""
    info "Uninstall (via curl):"
    echo "   curl -sSL https://raw.githubusercontent.com/EJAIS/vinylsticker/main/install.sh \\"
    echo "        -o /tmp/install.sh && bash /tmp/install.sh --uninstall"
    echo ""
}

main "$@"

#!/usr/bin/env bash
# Build vinyl-label-printer_<package version>_amd64.deb from the PyInstaller
# onedir bundle.
#
# Run after the PyInstaller build, on the system the bundle was built on
# (the linux job of .github/workflows/build.yml, Ubuntu 22.04):
#     pyinstaller --noconfirm --clean packaging/vinyl-label-printer.spec
#     PYTHON=/opt/venv/bin/python packaging/linux/build_deb.sh [OUTPUT_DIR]
#
# Requirements: fpm, dpkg, and in $PYTHON (default: python3) the packages that
# were bundled (the build venv), used to collect their licence files.
#
# Version: PACKAGE_VERSION and DEB_VERSION from packaging/package_version.sh
# (the CI passes both), e.g. 1.0.0-rc.1 and 1.0.0~rc.1 for the tag v1.0.0-rc.1.
# Without them, both are __version__ from vinyl-label-printer/__version__.py.
#
# Output: OUTPUT_DIR/vinyl-label-printer_<PACKAGE_VERSION>_amd64.deb (default:
# dist/). The file name uses PACKAGE_VERSION, never the "~" of DEB_VERSION
# (GitHub renames release assets with special characters). If $GITHUB_OUTPUT is
# set, "file=<file name>" is appended to it.
#
# Package layout:
#   /opt/vinyl-label-printer/                       PyInstaller bundle
#   /usr/bin/vinyl-label-printer                    symlink to the bundle executable
#   /usr/share/applications/vinyl-label-printer.desktop
#   /usr/share/icons/hicolor/<size>/apps/vinyl-label-printer.png
#   /usr/share/doc/vinyl-label-printer/copyright    DEP-5, incl. bundled components
#   /usr/share/doc/vinyl-label-printer/third-party/ verbatim licence texts

set -euo pipefail
umask 022   # fpm's own temp dirs end up in the package (e.g. "./")

NAME="vinyl-label-printer"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BUNDLE_DIR="$REPO_ROOT/dist/$NAME"
ICON_DIR="$REPO_ROOT/packaging/icons/hicolor"
COPYRIGHT="$SCRIPT_DIR/copyright"
OUTPUT_DIR="$(mkdir -p "${1:-$REPO_ROOT/dist}" && cd "${1:-$REPO_ROOT/dist}" && pwd)"
PYTHON="${PYTHON:-python3}"

die() { echo "ERROR: $*" >&2; exit 1; }

# Runtime dependencies. Everything else the bundle needs is shipped inside it
# by PyInstaller (checked with ldd on every ELF file of the bundle in a fresh
# ubuntu:22.04 container). In particular these are bundled and therefore NOT
# listed: libxcb-cursor0, libxkbcommon-x11-0, libxkbcommon0, libfontconfig1,
# libfreetype6, libdbus-1-3, libglib2.0-0, libx11-6, libx11-xcb1 and the whole
# libxcb-* set from build.yml (icccm4, image0, keysyms1, randr0, render-util0,
# render0, shape0, shm0, sync1, xfixes0, xkb1, util1, glx0).
# Not listed on purpose: the gtk3 platform theme plugin (needs GTK 3, loaded
# only when present; Qt falls back to its own theme) and the linuxfb plugin
# (libdrm, unused on a desktop).
DEPENDS=(
    # pdf2image renders the PDF preview with pdftoppm / pdfinfo.
    "poppler-utils"
    # "Print" opens the PDF in the default viewer via xdg-open.
    "xdg-utils"
    # libQt6Gui links libGL.so.1 and libEGL.so.1 directly; PyInstaller never
    # bundles them (they must match the system's graphics driver).
    "libgl1"
    "libegl1"
    # libxcb.so.1: needed by the xcb platform plugin (the X11 session of Mint)
    # and the bundled libX11 / libxcb-* libraries; excluded from bundling by
    # PyInstaller.
    "libxcb1"
    # Wayland platform plugin (libQt6WaylandClient): used in a Wayland session
    # (Mint 22 offers one). Not bundled by PyInstaller.
    "libwayland-client0"
    "libwayland-cursor0"
    "libwayland-egl1"
)

# ── Checks ────────────────────────────────────────────────────────────────────

[ -x "$BUNDLE_DIR/$NAME" ] || die "bundle not found: $BUNDLE_DIR (run PyInstaller first)"
command -v fpm >/dev/null || die "fpm not found (gem install fpm)"
command -v dpkg >/dev/null || die "dpkg not found (needed to locate licence files)"

if [ -z "${PACKAGE_VERSION:-}" ]; then
    [ -z "${DEB_VERSION:-}" ] || die "DEB_VERSION is set, but PACKAGE_VERSION is not"
    PACKAGE_VERSION="$("$PYTHON" -c "import runpy, sys; \
print(runpy.run_path(sys.argv[1])['__version__'])" \
        "$REPO_ROOT/$NAME/__version__.py")"
    [ -n "$PACKAGE_VERSION" ] || die "could not read the version"
    DEB_VERSION="$PACKAGE_VERSION"
fi
[ -n "${DEB_VERSION:-}" ] || die "PACKAGE_VERSION is set, but DEB_VERSION is not"
[[ "$PACKAGE_VERSION" =~ ^[0-9A-Za-z.-]+$ ]] \
    || die "PACKAGE_VERSION '$PACKAGE_VERSION' is not usable in a file name"
DEB_FILE="$OUTPUT_DIR/${NAME}_${PACKAGE_VERSION}_amd64.deb"
echo "Building $DEB_FILE (Debian version $DEB_VERSION)"

STAGING="$(mktemp -d)"
trap 'rm -rf "$STAGING"' EXIT
DOC_DIR="$STAGING/usr/share/doc/$NAME"

# ── Files ─────────────────────────────────────────────────────────────────────

mkdir -p "$STAGING/opt" "$STAGING/usr/bin" "$STAGING/usr/share/applications" "$DOC_DIR"
cp -a "$BUNDLE_DIR" "$STAGING/opt/$NAME"
# Symlink instead of a wrapper: the PyInstaller bootloader resolves its real
# location via /proc/self/exe, and argv[0] keeps the name used for WM_CLASS.
ln -s "/opt/$NAME/$NAME" "$STAGING/usr/bin/$NAME"

install -m 644 "$SCRIPT_DIR/$NAME.desktop" "$STAGING/usr/share/applications/$NAME.desktop"

for icon in "$ICON_DIR"/*/apps/"$NAME".png; do
    size="$(basename "$(dirname "$(dirname "$icon")")")"
    install -D -m 644 "$icon" "$STAGING/usr/share/icons/hicolor/$size/apps/$NAME.png"
done

install -m 644 "$COPYRIGHT" "$DOC_DIR/copyright"

# ── Third-party licence texts ─────────────────────────────────────────────────

# Debian copyright files of the system libraries PyInstaller copied into the
# bundle (regular *.so* files at the top of _internal/; symlinks there point
# into PyQt6/ and pillow.libs/), plus the Python runtime and standard library.
mkdir -p "$DOC_DIR/third-party/debian"
packages=("libpython3.10-stdlib")
while IFS= read -r lib; do
    name="$(basename "$lib")"
    pkg="$(dpkg -S "*/x86_64-linux-gnu/$name" 2>/dev/null | head -1 | cut -d: -f1)" \
        || true
    [ -n "$pkg" ] || die "no Debian package found for bundled library $name"
    packages+=("$pkg")
done < <(find "$STAGING/opt/$NAME/_internal" -maxdepth 1 -type f -name '*.so*')

missing=()
for pkg in $(printf '%s\n' "${packages[@]}" | sort -u); do
    cp -L "/usr/share/doc/$pkg/copyright" "$DOC_DIR/third-party/debian/$pkg.copyright"
    # Listed as the first word of an indented (Comment) line, e.g. " zlib1g ..."
    awk -v p="$pkg" '/^ / && $1 == p {found = 1} END {exit !found}' "$COPYRIGHT" \
        || missing+=("$pkg")
done
[ ${#missing[@]} -eq 0 ] || die "bundled packages not listed in $COPYRIGHT: ${missing[*]}"

# Licence files of the bundled Python distributions (runtime requirements and
# their dependencies) and of PyInstaller (bootloader).
"$PYTHON" - "$REPO_ROOT/$NAME/requirements.txt" "$DOC_DIR/third-party/python" \
    "$COPYRIGHT" <<'EOF'
import re
import shutil
import sys
from importlib.metadata import PackageNotFoundError, distribution
from pathlib import Path

from packaging.requirements import Requirement

req_file, out_dir, copyright_file = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
todo = [line.split("#")[0].strip() for line in Path(req_file).read_text().splitlines()]
todo = [Requirement(r).name for r in todo if r] + ["pyinstaller"]
seen = {}
while todo:
    name = todo.pop()
    key = re.sub(r"[-_.]+", "-", name).lower()
    if key in seen:
        continue
    try:
        dist = distribution(name)
    except PackageNotFoundError:
        sys.exit(f"ERROR: {name} is not installed in {sys.executable}")
    seen[key] = dist
    if key == "pyinstaller":
        continue  # only the bootloader is bundled, not PyInstaller's dependencies
    for req in map(Requirement, dist.requires or []):
        if req.marker is None or req.marker.evaluate({"extra": ""}):
            todo.append(req.name)

listed = Path(copyright_file).read_text().lower()
missing = []
for key, dist in sorted(seen.items()):
    files = [f for f in dist.files or []
             if re.search(r"LICEN[CS]E|COPYING|NOTICE", f.name, re.I)
             and ".dist-info/" in str(f)]
    if not files:
        sys.exit(f"ERROR: no licence file found for {key}")
    target = out_dir / f"{dist.metadata['Name']}-{dist.version}"
    target.mkdir(parents=True, exist_ok=True)
    for f in files:
        shutil.copyfile(f.locate(), target / f.name)
    if not re.search(rf"^ +{re.escape(key)}( |$)", listed, re.M):
        missing.append(key)
if missing:
    sys.exit(f"ERROR: Python packages not listed in {copyright_file}: {', '.join(missing)}")
print(f"Licence files of {len(seen)} Python distributions collected")
EOF

# Plain permissions (independent of the build user's umask).
chmod -R u+rwX,go+rX,go-w "$STAGING"

# ── Package ───────────────────────────────────────────────────────────────────

depends_args=()
for dep in "${DEPENDS[@]}"; do
    depends_args+=(--depends "$dep")
done

rm -f "$DEB_FILE"
fpm -s dir -t deb \
    --name "$NAME" \
    --version "$DEB_VERSION" \
    --architecture amd64 \
    --maintainer "Alexander <125554454+EJAIS@users.noreply.github.com>" \
    --vendor "EJAIS" \
    --url "https://github.com/EJAIS/vinylsticker" \
    --license "GPL-3.0" \
    --category misc \
    --deb-priority optional \
    --description "Print labels for 7\" vinyl records
Vinyl Label Printer creates print-ready PDFs of labels for 7\" vinyl records
on Avery Zweckform 4780 sheets (A4, 40 labels per sheet). Records come from a
local Excel database or from a Discogs collection, can be reviewed and edited
before printing, and are printed from the system's PDF viewer at 100 % scale.
The package contains a self-contained build with its own Python and Qt 6." \
    "${depends_args[@]}" \
    --after-install "$SCRIPT_DIR/refresh-caches.sh" \
    --after-remove "$SCRIPT_DIR/refresh-caches.sh" \
    --deb-no-default-config-files \
    --package "$DEB_FILE" \
    -C "$STAGING" \
    opt usr

built_version="$(dpkg-deb --field "$DEB_FILE" Version)"
[ "$built_version" = "$DEB_VERSION" ] \
    || die "package has Debian version '$built_version', expected '$DEB_VERSION'"

echo "Built $DEB_FILE"
if [ -n "${GITHUB_OUTPUT:-}" ]; then
    echo "file=$(basename "$DEB_FILE")" >> "$GITHUB_OUTPUT"
fi

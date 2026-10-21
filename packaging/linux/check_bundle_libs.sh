#!/usr/bin/env bash
# Check that every shared library needed by the installed bundle resolves,
# i.e. that the package's Depends are complete. Used by the deb-install-test
# CI job right after "apt-get install ./vinyl-label-printer_*.deb" on a fresh
# system.
#
# Usage: packaging/linux/check_bundle_libs.sh [/opt/vinyl-label-printer]
#
# Plugins that are allowed to have unresolved libraries (Qt skips a plugin it
# cannot load and falls back):
#   platformthemes/libqgtk3.so   GTK 3 theme, only used where GTK 3 is present
#   platforms/libqlinuxfb.so     framebuffer platform (libdrm), not used on a desktop

set -euo pipefail

BUNDLE="${1:-/opt/vinyl-label-printer}"
OPTIONAL_RE='/(platformthemes/libqgtk3|platforms/libqlinuxfb)\.so$'
export LD_LIBRARY_PATH="$BUNDLE/_internal:$BUNDLE/_internal/PyQt6/Qt6/lib"

checked=0
failed=0
while IFS= read -r -d '' file; do
    head -c 4 "$file" | grep -q 'ELF' || continue
    checked=$((checked + 1))
    missing="$(ldd "$file" 2>/dev/null | awk '/not found/ {print $1}' | sort -u | tr '\n' ' ')"
    [ -n "$missing" ] || continue
    if [[ "$file" =~ $OPTIONAL_RE ]]; then
        echo "optional: ${file#"$BUNDLE"/} needs $missing"
    else
        echo "MISSING:  ${file#"$BUNDLE"/} needs $missing"
        failed=$((failed + 1))
    fi
done < <(find "$BUNDLE" -type f \( -name '*.so*' -o -perm -u+x \) -print0)

echo "$checked ELF files checked, $failed with unresolved libraries"
[ "$failed" -eq 0 ]

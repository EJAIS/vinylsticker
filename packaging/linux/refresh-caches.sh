#!/bin/sh
# after-install / after-remove script of the .deb (see build_deb.sh).
# Refreshes the system-wide icon cache and desktop database so the menu entry
# and icon appear / disappear without a re-login. Only system directories are
# touched, never anything in users' home directories. Failures are ignored so
# they can never break an install or removal.
set -e

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor || true
fi

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || true
fi

exit 0

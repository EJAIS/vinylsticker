"""
Environment inherited by the programs the app starts: xdg-open and what it
launches (file manager, browser, PDF viewer), QDesktopServices.openUrl and
pdf2image's pdfinfo / pdftoppm.
"""

from __future__ import annotations

import os
import sys

# Variables that only describe the PyInstaller bundle. None of them existed
# before the app started (the PyQt6 runtime hook overwrites a user's own
# QT_PLUGIN_PATH without saving it), so they are removed, not restored.
_BUNDLE_ONLY_VARS = (
    "LD_LIBRARY_PATH_ORIG",         # bootloader: copy of the user's LD_LIBRARY_PATH
    "QT_PLUGIN_PATH",               # PyQt6 runtime hook: <bundle>/PyQt6/Qt6/plugins
    "QML2_IMPORT_PATH",             # PyQt6 runtime hook: <bundle>/PyQt6/Qt6/qml
    "_PYI_ARCHIVE_FILE",            # bootloader internals, incl. the bundle path
    "_PYI_APPLICATION_HOME_DIR",
    "_PYI_PARENT_PROCESS_LEVEL",
    "_PYI_LINUX_PROCESS_NAME",
    "_PYI_SPLASH_IPC",
)


def restore_user_environment() -> None:
    """Give child processes the environment the user started the app with.

    Only for the frozen Linux build; from source and on Windows this does
    nothing. Must run before QApplication is created.

    Why: the PyInstaller bootloader prepends the bundle's _internal/ to
    LD_LIBRARY_PATH and re-executes itself so the app loads its bundled
    libraries. Every child process inherits that variable and then loads the
    bundle's older libstdc++ / glib instead of the system ones, and crashes
    (nemo: "GLIBCXX_3.4.32 not found", browsers: "undefined symbol
    g_once_init_leave_pointer"). Likewise QT_PLUGIN_PATH would make a system
    Qt app (e.g. Okular) load the bundle's Qt plugins.

    Changing os.environ here does not affect the running app: glibc reads
    LD_LIBRARY_PATH only at process start, and Qt finds its plugins through
    the qt.conf that PyQt6 embeds (QT_PLUGIN_PATH points to the same folder).
    subprocess, QProcess, QDesktopServices and pdf2image all copy os.environ
    when they start a program, so this one place covers all of them.
    LD_LIBRARY_PATH is restored as described in the PyInstaller docs
    ("Runtime information" > "LD_LIBRARY_PATH / LIBPATH considerations").
    """
    if not (getattr(sys, "frozen", False) and sys.platform.startswith("linux")):
        return

    original = os.environ.get("LD_LIBRARY_PATH_ORIG")
    if original is not None:
        os.environ["LD_LIBRARY_PATH"] = original
    else:
        os.environ.pop("LD_LIBRARY_PATH", None)

    for name in _BUNDLE_ONLY_VARS:
        os.environ.pop(name, None)

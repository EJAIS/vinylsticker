# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Vinyl Label Printer (onedir, windowed).

Build from the repository root:
    pyinstaller --noconfirm --clean packaging/vinyl-label-printer.spec

Output: dist/vinyl-label-printer/ (executable + _internal/ with all resources).

Qt: the app only imports QtCore, QtGui and QtWidgets. PyInstaller's own PyQt6
hooks already collect the Qt plugins these modules need (platforms,
platformthemes, styles, imageformats, iconengines, xcbglintegrations,
wayland*), so no hidden imports are required. Lazy imports inside functions
(e.g. ui.discogs_dialog, pdf2image) are found by the static import analysis.
"""

import sys
from pathlib import Path

SPEC_DIR = Path(SPECPATH)
REPO_ROOT = SPEC_DIR.parent
APP_DIR = REPO_ROOT / "vinyl-label-printer"

# Read-only resources, resolved at runtime via modules.paths.resource_path()
datas = [
    (str(APP_DIR / "config" / "credentials.example.json"), "config"),
    (str(REPO_ROOT / "examples"), "examples"),
]

# Windows only: bundle Poppler (pdftoppm/pdfinfo + DLLs) if it was downloaded to
# packaging/poppler. Added as data so PyInstaller copies the folder unchanged;
# the Poppler executables run as separate processes from poppler/bin.
POPPLER_DIR = SPEC_DIR / "poppler"
if sys.platform == "win32" and POPPLER_DIR.is_dir():
    datas.append((str(POPPLER_DIR), "poppler"))

a = Analysis(
    [str(APP_DIR / "main.py")],
    pathex=[str(APP_DIR)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="vinyl-label-printer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # TODO: set the app icon (.ico on Windows) in a later step
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="vinyl-label-printer",
)

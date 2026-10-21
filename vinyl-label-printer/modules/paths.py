"""
Filesystem locations of resources shipped with the application.

Works both when running from source and when frozen by PyInstaller.
Only read-only resources are resolved here; writable user data still lives
next to the source tree for now.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Root of the read-only resources: the vinyl-label-printer/ folder when running
# from source, the PyInstaller bundle directory (sys._MEIPASS) when frozen.
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    _RESOURCE_ROOT = Path(sys._MEIPASS)
else:
    _RESOURCE_ROOT = Path(__file__).resolve().parent.parent


def resource_path(relative: str | Path) -> Path:
    """Return the absolute path of a read-only resource shipped with the app.

    Args:
        relative: Path relative to the resource root,
                  e.g. ``"config/credentials.example.json"``.
    """
    return _RESOURCE_ROOT / relative


def get_poppler_path() -> str | None:
    """Return the bundled Poppler ``bin`` folder, or None to use the system PATH.

    Poppler is only bundled with the Windows build; on Linux (and when running
    from source) this returns None so pdf2image falls back to the system PATH.
    """
    poppler_bin = resource_path("poppler/bin")
    return str(poppler_bin) if poppler_bin.is_dir() else None

"""
Cross-platform print trigger.

Opens the OS print dialog for the generated PDF without embedding a printer
driver — the OS / printer driver handles all scaling.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def print_pdf(pdf_path: Path) -> None:
    """Open the OS print dialog for *pdf_path*.

    Platform behaviour:
      Windows  — os.startfile(path, "print") hands the file to the default
                 PDF application with the "print" verb, which opens the
                 system print dialog.
      Linux    — tries ``lp`` (CUPS); falls back to ``xdg-open`` which opens
                 the file in the default viewer (e.g. Evince) where the user
                 can print manually.
      macOS    — opens the file in Preview via ``open -a Preview``.

    Args:
        pdf_path: Absolute or relative path to the PDF file.

    Raises:
        FileNotFoundError: If *pdf_path* does not exist.
        RuntimeError: If the print command fails on Linux/macOS.
    """
    pdf_path = Path(pdf_path).resolve()
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    if sys.platform == "win32":
        _print_windows(pdf_path)
    elif sys.platform == "darwin":
        _print_macos(pdf_path)
    else:
        _print_linux(pdf_path)


# ── Platform implementations ──────────────────────────────────────────────────

def _print_windows(pdf_path: Path) -> None:
    import os
    try:
        os.startfile(str(pdf_path), "print")
    except OSError:
        # WinError 1155: default PDF viewer does not register the "print"
        # shell verb (common with Microsoft Edge on Windows 11).
        # Fall back to opening the file so the user can print manually.
        os.startfile(str(pdf_path))


def _print_linux(pdf_path: Path) -> None:
    """Try CUPS ``lp``; fall back to ``xdg-open`` if lp is not available."""
    try:
        subprocess.run(
            ["lp", str(pdf_path)],
            check=True,
            capture_output=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        # xdg-open opens the PDF viewer; the user prints from there
        result = subprocess.run(
            ["xdg-open", str(pdf_path)],
            capture_output=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"xdg-open failed (exit {result.returncode}): "
                f"{result.stderr.decode(errors='replace')}"
            )


def _print_macos(pdf_path: Path) -> None:
    result = subprocess.run(
        ["open", "-a", "Preview", str(pdf_path)],
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"open -a Preview failed (exit {result.returncode}): "
            f"{result.stderr.decode(errors='replace')}"
        )

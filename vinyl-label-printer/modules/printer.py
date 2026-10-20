"""
Cross-platform print trigger.

Hands the generated PDF to the OS so the user prints it from a print dialog
(Windows: print verb / viewer, Linux: default PDF viewer via xdg-open,
macOS: Preview).  Nothing is sent to a printer without a dialog, so the user
can always choose "Actual size / 100 %".
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PyQt6.QtWidgets import QCheckBox, QMessageBox

from config.settings import get_show_print_hint, set_show_print_hint
from modules.i18n import t


def print_pdf(pdf_path: Path) -> None:
    """Open the OS print dialog for *pdf_path*.

    Platform behaviour:
      Windows  — os.startfile(path, "print") hands the file to the default
                 PDF application with the "print" verb, which opens the
                 system print dialog.
      Linux    — opens the file in the default PDF viewer via ``xdg-open``
                 (e.g. Evince, Xreader); the user prints from the viewer's
                 print dialog.  No job is sent to the printer directly.
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

    if get_show_print_hint():
        _show_print_hint()

    if sys.platform == "win32":
        _print_windows(pdf_path)
    elif sys.platform == "darwin":
        _print_macos(pdf_path)
    else:
        _print_linux(pdf_path)


# ── Print hint dialog ─────────────────────────────────────────────────────────

def _show_print_hint() -> None:
    """Show a one-time reminder to use 'Actual Size' (100 %) in the print dialog."""
    msg = QMessageBox()
    msg.setWindowTitle(t("print_hint_title"))
    msg.setText(t("print_hint_text"))
    msg.setIcon(QMessageBox.Icon.Information)
    msg.setStandardButtons(QMessageBox.StandardButton.Ok)

    chk = QCheckBox(t("dont_show_again"))
    msg.setCheckBox(chk)

    msg.exec()

    if chk.isChecked():
        set_show_print_hint(False)


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
    """Open *pdf_path* in the default PDF viewer via ``xdg-open``.

    Direct printing via ``lp`` is intentionally not used: it gives no control
    over scaling, and driverless IPP printers may auto-scale the full-page
    label sheet.  Printing from the viewer's dialog matches Windows / macOS.
    """
    try:
        result = subprocess.run(
            ["xdg-open", str(pdf_path)],
            capture_output=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("xdg-open not found — cannot open the PDF viewer") from exc
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

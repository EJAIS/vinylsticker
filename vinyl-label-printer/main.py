"""
Entry point for the Vinyl Label Printer application.

Usage:
    python main.py
"""

import sys
from pathlib import Path

# Ensure the project root is on sys.path so that package imports work
# regardless of the working directory from which the script is launched.
_ROOT = Path(__file__).parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import qdarktheme
from PyQt6.QtCore import Qt

from __version__ import __version__
from PyQt6.QtWidgets import QApplication
from config.settings import get_theme
from ui.app import MainWindow


def _resolve_theme(app: QApplication, theme: str) -> str:
    """Resolve "auto" to "dark" or "light" based on the OS color scheme."""
    if theme != "auto":
        return theme
    scheme = app.styleHints().colorScheme()
    return "dark" if scheme == Qt.ColorScheme.Dark else "light"


def apply_theme(app: QApplication, theme: str) -> None:
    resolved = _resolve_theme(app, theme)
    app.setStyleSheet(qdarktheme.load_stylesheet(resolved))
    app.setPalette(qdarktheme.load_palette(resolved))


def main() -> None:
    app = QApplication(sys.argv)
    apply_theme(app, get_theme())
    app.setApplicationName("Vinyl-Label-Drucker")
    window = MainWindow()
    window.setWindowTitle(f"Vinyl Label Printer v{__version__}")
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

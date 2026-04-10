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

from PyQt6.QtCore import Qt

from __version__ import __version__
from PyQt6.QtWidgets import QApplication
from config.settings import (
    get_theme as get_saved_theme,
    get_language_setting,
    get_debug_logging,
    get_data_source_mode,
)
from config.themes import get_theme
from config.stylesheet import build_stylesheet
from modules.i18n import set_language
from modules.logger import setup_logger, get_logger
from ui.app import MainWindow


def _resolve_theme(app: QApplication, theme: str) -> str:
    """Resolve "auto" to "dark" or "light" based on the OS color scheme."""
    if theme != "auto":
        return theme
    scheme = app.styleHints().colorScheme()
    return "dark" if scheme == Qt.ColorScheme.Dark else "light"


def apply_theme(app: QApplication, theme: str) -> None:
    resolved = _resolve_theme(app, theme)
    colors = get_theme(resolved)
    app.setStyleSheet(build_stylesheet(colors))
    app.setProperty("theme_colors", colors)


def main() -> None:
    debug_enabled = get_debug_logging()
    setup_logger(debug=debug_enabled)
    logger = get_logger()

    logger.info("=" * 50)
    logger.info(f"App started — v{__version__}")
    logger.info(f"Platform: {sys.platform}")
    logger.info(f"Python: {sys.version.split()[0]}")
    logger.info(f"Debug logging: {debug_enabled}")
    logger.info(f"Theme: {get_saved_theme()}")
    logger.info(f"Language: {get_language_setting()}")
    logger.info(f"Data source: {get_data_source_mode().value}")
    logger.info("=" * 50)

    if debug_enabled:
        logger.info("Debug logging active (persistent)")

    app = QApplication(sys.argv)
    apply_theme(app, get_saved_theme())
    set_language(get_language_setting())
    app.setApplicationName("Vinyl-Label-Drucker")
    window = MainWindow()
    window.setWindowTitle(f"Vinyl Label Printer v{__version__}")
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

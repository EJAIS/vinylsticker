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

from PyQt6.QtWidgets import QApplication
from ui.app import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Vinyl-Label-Drucker")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

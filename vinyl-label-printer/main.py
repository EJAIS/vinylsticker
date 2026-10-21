"""
Entry point for the Vinyl Label Printer application.

Usage:
    python main.py
    python main.py --version   # print name and version, then exit
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
from PyQt6.QtGui import QIcon
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
from modules.paths import (
    MigrationResult,
    get_app_icon_file,
    get_config_dir,
    get_data_dir,
    get_cache_dir,
    get_log_dir,
    migrate_legacy_data,
    seed_example_database,
)
from ui.app import MainWindow

APP_NAME = "Vinyl Label Printer"
# Windows taskbar identity; see _set_windows_app_id()
APP_USER_MODEL_ID = "EJAIS.VinylLabelPrinter"


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


def _print_version() -> None:
    """Print the app name and version to stdout.

    A windowed (GUI-subsystem) Windows build has no stdout; attach to the
    parent console if there is one so the output is still visible.
    """
    if sys.stdout is None and sys.platform == "win32":
        import ctypes
        if ctypes.windll.kernel32.AttachConsole(-1):   # ATTACH_PARENT_PROCESS
            sys.stdout = open("CONOUT$", "w", encoding="utf-8")
    if sys.stdout is not None:
        print(f"{APP_NAME} {__version__}")
        sys.stdout.flush()


def _set_windows_app_id() -> None:
    """Give the process its own AppUserModelID on Windows.

    Without it, a run from source is grouped under python.exe in the taskbar
    and shows the Python icon instead of the window icon. Must run before the
    first window is created. Failures are logged and ignored.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception as exc:
        get_logger().warning(f"Could not set AppUserModelID: {exc}")


def _apply_app_icon(app: QApplication) -> None:
    """Set the application-wide window icon, if the icon file is available."""
    icon_file = get_app_icon_file()
    if icon_file is None:
        get_logger().warning("App icon not found — using the default icon")
        return
    app.setWindowIcon(QIcon(str(icon_file)))


def _log_data_setup(
    migration: MigrationResult,
    seeded: Path | None,
    seed_error: str | None,
) -> None:
    """Log the outcome of the legacy migration and database seeding."""
    logger = get_logger()
    logger.info(f"Config dir: {get_config_dir()}")
    logger.info(f"Data dir:   {get_data_dir()}")
    logger.info(f"Cache dir:  {get_cache_dir()}")
    logger.info(f"Log dir:    {get_log_dir()}")

    # One-time events are logged as warnings so they show up in app.log at the
    # default (non-debug) log level.
    if migration.already_done:
        logger.debug("Legacy data migration already done — skipped")
    elif migration.copied:
        for src, dst in migration.copied:
            logger.warning(f"Legacy data migrated: {src} -> {dst}")
    else:
        logger.info("Legacy data migration: nothing to copy")
    for error in migration.errors:
        logger.error(f"Legacy data migration failed: {error} (will retry on next start)")

    if seeded is not None:
        logger.warning(f"Example database copied to: {seeded}")
    if seed_error is not None:
        logger.warning(f"Could not create the example database: {seed_error}")


def main() -> None:
    # Runs after all module imports and before QApplication is created, so the
    # frozen build can use it as an import smoke test.
    if "--version" in sys.argv[1:]:
        _print_version()
        sys.exit(0)

    # Copy data from the legacy app-relative layout before anything reads
    # settings or opens the log file; results are logged once logging exists.
    migration = migrate_legacy_data()
    seeded, seed_error = None, None
    if not migration.errors:
        # Skipped after a failed migration so a seeded example can never block
        # the retry of the user's own database.xlsx on the next start.
        seeded, seed_error = seed_example_database()

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

    _log_data_setup(migration, seeded, seed_error)

    _set_windows_app_id()
    app = QApplication(sys.argv)
    _apply_app_icon(app)
    apply_theme(app, get_saved_theme())
    set_language(get_language_setting())
    app.setApplicationName("Vinyl-Label-Drucker")
    window = MainWindow()   # sets its own title incl. version
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

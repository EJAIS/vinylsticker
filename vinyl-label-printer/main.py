"""
Entry point for the Vinyl Label Printer application.

Usage:
    python main.py
    python main.py --version   # print name and version, then exit

Hidden diagnostic (CI): --print-child-env, see _print_child_env().
"""

import os
import sys
from pathlib import Path

# Ensure the project root is on sys.path so that package imports work
# regardless of the working directory from which the script is launched.
_ROOT = Path(__file__).parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from __version__ import __version__
from PyQt6.QtGui import QGuiApplication, QIcon
from PyQt6.QtWidgets import QApplication, QMessageBox
from config.settings import (
    get_theme as get_saved_theme,
    get_language_setting,
    get_debug_logging,
    get_data_source_mode,
)
from modules.child_env import restore_user_environment
from modules.i18n import set_language, t
from modules.logger import setup_logger, get_logger
from modules.paths import (
    MigrationResult,
    get_app_icon_file,
    get_config_dir,
    get_data_dir,
    get_cache_dir,
    get_log_dir,
    get_poppler_path,
    migrate_legacy_data,
)
from modules.xlsx_migration import (
    ALREADY_DONE,
    MIGRATED,
    NO_XLSX,
    XlsxMigrationResult,
    migrate_xlsx_queue,
)
from ui.app import MainWindow
from ui.theme_manager import ThemeManager

APP_NAME = "Vinyl Label Printer"
# Windows taskbar identity; see _set_windows_app_id()
APP_USER_MODEL_ID = "EJAIS.VinylLabelPrinter"
# Linux window matching; keep in sync with packaging/linux/vinyl-label-printer.desktop:
# DESKTOP_FILE_NAME is the basename of the .desktop file (Wayland app_id, X11
# _GTK_APPLICATION_ID), QT_APP_NAME is the WM_CLASS class on X11 (StartupWMClass=).
DESKTOP_FILE_NAME = "vinyl-label-printer"
QT_APP_NAME = "Vinyl-Label-Drucker"


def _attach_parent_console() -> None:
    """Make stdout usable for command-line output.

    A windowed (GUI-subsystem) Windows build has no stdout; attach to the
    parent console if there is one so the output is still visible.
    """
    if sys.stdout is None and sys.platform == "win32":
        import ctypes
        if ctypes.windll.kernel32.AttachConsole(-1):   # ATTACH_PARENT_PROCESS
            sys.stdout = open("CONOUT$", "w", encoding="utf-8")


def _print_version() -> None:
    """Print the app name and version to stdout."""
    _attach_parent_console()
    if sys.stdout is not None:
        print(f"{APP_NAME} {__version__}")
        sys.stdout.flush()


def _print_child_env() -> int:
    """Print the environment child processes inherit, one NAME=value per line.

    Then runs the PDF preview's Poppler call (pdf2image -> pdfinfo, pdftoppm)
    once on a generated one-page PDF and reports the result on a line starting
    with "# ". Used by CI to check that no bundle path reaches child processes.
    Returns the exit code: 0 if the Poppler call worked, 1 otherwise.
    """
    _attach_parent_console()
    if sys.stdout is None:
        return 1
    for name in sorted(os.environ):
        print(f"{name}={os.environ[name]}")
    try:
        import tempfile
        from pdf2image import convert_from_path
        from reportlab.pdfgen import canvas

        with tempfile.TemporaryDirectory() as tmp:
            pdf = Path(tmp) / "child-env-check.pdf"
            page = canvas.Canvas(str(pdf))
            page.drawString(72, 72, APP_NAME)
            page.save()
            pages = convert_from_path(str(pdf), dpi=10, poppler_path=get_poppler_path())
        print(f"# pdf2image: OK ({len(pages)} page)")
        return 0
    except Exception as exc:
        print(f"# pdf2image: FAILED: {type(exc).__name__}: {exc}")
        return 1
    finally:
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
    xlsx_migration: XlsxMigrationResult | None,
) -> None:
    """Log the outcome of the legacy migration and the database.xlsx migration."""
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

    result = xlsx_migration
    if result is None:
        logger.warning(
            "database.xlsx migration skipped because the legacy data migration "
            "failed (will retry on next start)"
        )
    elif result.status == ALREADY_DONE:
        logger.debug("database.xlsx migration already done — skipped")
    elif result.status == NO_XLSX:
        logger.warning(
            f"database.xlsx migration: no file at {result.xlsx_path} — "
            "starting with an empty print queue"
        )
    elif result.status == MIGRATED:
        logger.warning(
            f"database.xlsx migrated: {result.rows} rows of the Print sheet "
            f"copied from {result.xlsx_path} into labels.db (the xlsx is unchanged)"
        )
        if result.database_rows:
            logger.warning(
                f"database.xlsx: the Database sheet has {result.database_rows} rows; "
                "it was never used by the app and stays in the xlsx"
            )
    else:
        logger.error(
            f"database.xlsx migration failed: {result.error} "
            f"(file: {result.xlsx_path}; will retry on next start)"
        )


def main() -> None:
    # First, so that every program started from here on gets the user's
    # environment, not the bundle's (see restore_user_environment()).
    restore_user_environment()

    # Runs after all module imports and before QApplication is created, so the
    # frozen build can use it as an import smoke test.
    if "--version" in sys.argv[1:]:
        _print_version()
        sys.exit(0)
    if "--print-child-env" in sys.argv[1:]:
        sys.exit(_print_child_env())

    # Copy data from the legacy app-relative layout before anything reads
    # settings or opens the log file; results are logged once logging exists.
    migration = migrate_legacy_data()

    debug_enabled = get_debug_logging()
    setup_logger(debug=debug_enabled)
    logger = get_logger()

    logger.info("=" * 50)
    logger.info(f"App started — v{__version__}")
    logger.info(f"Platform: {sys.platform}")
    logger.info(f"Python: {sys.version.split()[0]}")
    logger.info(f"Debug logging: {debug_enabled}")
    logger.info(f"Theme setting: {get_saved_theme()}")
    logger.info(f"Language: {get_language_setting()}")
    logger.info(f"Data source: {get_data_source_mode().value}")
    logger.info("=" * 50)

    if debug_enabled:
        logger.info("Debug logging active (persistent)")

    # Print queue: take over the database.xlsx of an older version once (it may
    # have just been copied by the legacy migration). Skipped after a failed
    # legacy migration so a missing copy never sets the "nothing to migrate"
    # marker; both are retried on the next start.
    xlsx_migration = migrate_xlsx_queue() if not migration.errors else None
    _log_data_setup(migration, xlsx_migration)

    _set_windows_app_id()
    app = QApplication(sys.argv)
    QGuiApplication.setDesktopFileName(DESKTOP_FILE_NAME)
    _apply_app_icon(app)
    ThemeManager.instance().set_setting(get_saved_theme(), persist=False)
    set_language(get_language_setting())
    # Must stay before the first window is created: Qt reads it for WM_CLASS then.
    app.setApplicationName(QT_APP_NAME)
    window = MainWindow()   # sets its own title incl. version
    window.show()
    if xlsx_migration is not None and xlsx_migration.failed:
        QMessageBox.warning(
            window, t("app_title"),
            t("xlsx_migration_failed_msg", path=str(xlsx_migration.xlsx_path)),
        )
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

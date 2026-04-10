import logging
import logging.handlers
from pathlib import Path

LOG_FILE = Path(__file__).parent.parent / "logs" / "app.log"
LOG_FORMAT = "%(asctime)s [%(levelname)-8s] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
MAX_BYTES = 2 * 1024 * 1024  # 2 MB
BACKUP_COUNT = 3              # keep app.log, app.log.1, app.log.2


def setup_logger(debug: bool = False) -> logging.Logger:
    """Set up the application logger. Call once in main.py on startup.

    debug=True  — level DEBUG, logs to file + console
    debug=False — level WARNING, logs to file only
    """
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("vinyl_label_printer")
    logger.setLevel(logging.DEBUG if debug else logging.WARNING)
    logger.handlers.clear()

    # Rotating file handler — always active
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG if debug else logging.WARNING)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    logger.addHandler(file_handler)

    # Console handler — only in debug mode
    if debug:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
        logger.addHandler(console_handler)

    return logger


def get_logger() -> logging.Logger:
    """Return the application logger. Use this in all modules."""
    return logging.getLogger("vinyl_label_printer")


def set_debug_mode(enabled: bool) -> None:
    """Toggle debug mode at runtime without a restart.

    Called when the user changes the setting in SettingsDialog.
    """
    logger = get_logger()
    level = logging.DEBUG if enabled else logging.WARNING
    logger.setLevel(level)
    for handler in logger.handlers:
        handler.setLevel(level)

    if enabled:
        # Add console handler if not already present
        has_console = any(
            isinstance(h, logging.StreamHandler)
            and not isinstance(h, logging.handlers.RotatingFileHandler)
            for h in logger.handlers
        )
        if not has_console:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)
            console_handler.setFormatter(
                logging.Formatter(LOG_FORMAT, DATE_FORMAT)
            )
            logger.addHandler(console_handler)
        logger.info("Debug logging enabled")
    else:
        # Remove console handlers
        logger.handlers = [
            h for h in logger.handlers
            if isinstance(h, logging.handlers.RotatingFileHandler)
        ]
        logger.warning("Debug logging disabled")

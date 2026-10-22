"""
Small JSON files that must survive a crash: settings.json and credentials.json.

write_json() never leaves a half-written file behind: the data goes to a
temporary file in the same directory, is flushed to disk (fsync) and then
replaces the target in one step (os.replace, atomic on Linux and Windows).
On Windows os.replace can fail for a moment while a virus scanner or the
search indexer holds the target open; it is retried a few times.

read_json() moves a file that cannot be read as a JSON object aside to
<name>.corrupt-YYYYmmdd-HHMMSS before the caller goes on with its defaults,
so the next write cannot destroy what was in it. If the file can neither be
read nor moved aside, writes to it are refused for the rest of the session.
Only paths are logged, never file contents (credentials.json holds a token).
settings.json is read before the log file exists (main.py: debug setting);
messages from that time are kept and written by log_early_messages().
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import time
from datetime import datetime
from pathlib import Path

from modules.logger import get_logger

logger = get_logger()

_REPLACE_ATTEMPTS = 5
_REPLACE_DELAY_S = 0.05

# Files that could not be read and not be moved aside: never overwritten
_blocked: set[Path] = set()

# Messages logged while the application logger had no handler yet
_early_messages: list[tuple[int, str]] = []


def _log(level: int, message: str) -> None:
    if not logger.hasHandlers():
        _early_messages.append((level, message))
    logger.log(level, message)


def log_early_messages() -> None:
    """Log the messages from before setup_logger() again, now into app.log."""
    while _early_messages:
        logger.log(*_early_messages.pop(0))


def _replace(source: Path, target: Path) -> None:
    """os.replace, retried on PermissionError (Windows: file briefly held open)."""
    for attempt in range(_REPLACE_ATTEMPTS):
        try:
            os.replace(source, target)
            return
        except PermissionError:
            if attempt == _REPLACE_ATTEMPTS - 1:
                raise
            time.sleep(_REPLACE_DELAY_S)


def _fsync_dir(folder: Path) -> None:
    """Persist the rename itself (POSIX); not possible / needed on Windows."""
    if os.name != "posix":
        return
    try:
        fd = os.open(folder, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def write_json(path: Path, data: dict, mode: int = 0o644) -> bool:
    """Atomically replace *path* with *data* as JSON; False if the write was refused.

    *mode*: file permissions of the new file (POSIX; e.g. 0o600 for secrets).

    Raises:
        OSError: if the file could not be written (the old content is kept).
    """
    if path in _blocked:
        _log(logging.ERROR, f"Not writing {path}: it could not be read or moved aside")
        return False
    text = json.dumps(data, indent=2, ensure_ascii=False)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.chmod(tmp, mode)
        except (NotImplementedError, OSError):
            pass  # Windows ignores most mode bits anyway
        _replace(tmp, path)
    except BaseException:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise
    _fsync_dir(path.parent)
    return True


def _corrupt_name(path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    candidate = path.with_name(f"{path.name}.corrupt-{stamp}")
    counter = 1
    while candidate.exists():
        candidate = path.with_name(f"{path.name}.corrupt-{stamp}-{counter}")
        counter += 1
    return candidate


def _move_aside(path: Path, reason: str) -> None:
    target = _corrupt_name(path)
    try:
        _replace(path, target)
    except OSError as exc:
        _blocked.add(path)
        _log(
            logging.ERROR,
            f"{path} is unreadable ({reason}) and could not be moved aside "
            f"({type(exc).__name__}); it will not be overwritten in this session",
        )
        return
    _log(
        logging.WARNING,
        f"{path} was unreadable ({reason}); moved aside to {target}, using defaults",
    )


def read_json(path: Path) -> dict | None:
    """The JSON object in *path*; None if the file is missing or unusable.

    An unusable file (not JSON, not an object, not UTF-8) is moved aside
    first; a file that cannot be opened at all is left as it is and blocked
    for writes (see module docstring).
    """
    if not path.exists():
        return None
    try:
        raw = path.read_bytes()
    except OSError as exc:
        _blocked.add(path)
        _log(
            logging.ERROR,
            f"Could not read {path} ({type(exc).__name__}); "
            "it will not be overwritten in this session",
        )
        return None
    try:
        data = json.loads(raw.decode("utf-8"))
    except ValueError as exc:     # JSONDecodeError and UnicodeDecodeError
        _move_aside(path, type(exc).__name__)
        return None
    if not isinstance(data, dict):
        _move_aside(path, f"top level is {type(data).__name__}, not an object")
        return None
    _blocked.discard(path)
    return data

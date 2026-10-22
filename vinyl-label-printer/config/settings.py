"""
Persistent application settings stored as JSON.

Currently stores:
  watermark_path    — absolute path string, or null
  data_source_mode  — "local" or "discogs"
  theme             — "auto", "dark", or "light"
  save_to_collection — queue editor (LOCAL mode): "Also save to collection"
  window_geometry   — {window key: base64 of QWidget.saveGeometry()}
  header_state      — {window key: {"columns": n, "state": base64 of
                      QHeaderView.saveState()}}
"""

from __future__ import annotations

import base64
import binascii
import json
from pathlib import Path

from modules.data_source import DataSourceMode
from modules.paths import get_settings_file


def _load() -> dict:
    settings_file = get_settings_file()
    if settings_file.exists():
        try:
            return json.loads(settings_file.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save(data: dict) -> None:
    get_settings_file().write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def get_watermark_path() -> Path | None:
    """Return the saved watermark path, or None if not set."""
    value = _load().get("watermark_path")
    return Path(value) if value else None


def set_watermark_path(path: Path | None) -> None:
    """Persist *path* as the watermark. Pass None to clear."""
    data = _load()
    data["watermark_path"] = str(path) if path is not None else None
    _save(data)


def get_data_source_mode() -> DataSourceMode:
    """Return the saved data source mode, defaulting to LOCAL."""
    value = _load().get("data_source_mode", "local")
    try:
        return DataSourceMode(value)
    except ValueError:
        return DataSourceMode.LOCAL


def set_data_source_mode(mode: DataSourceMode) -> None:
    """Persist *mode* as the active data source."""
    data = _load()
    data["data_source_mode"] = mode.value
    _save(data)


def get_theme() -> str:
    """Return the saved theme ("auto", "dark", or "light"), defaulting to "auto"."""
    val = _load().get("theme", "auto")
    return val if val in ("auto", "dark", "light") else "auto"


def set_theme(theme: str) -> None:
    """Persist *theme* as the active UI theme."""
    data = _load()
    data["theme"] = theme
    _save(data)


def get_language_setting() -> str:
    """Return saved language code ("DE" or "EN"), defaulting to "DE"."""
    val = _load().get("language", "DE")
    return val if val in ("DE", "EN") else "DE"


def set_language_setting(code: str) -> None:
    """Persist *code* as the active UI language."""
    data = _load()
    data["language"] = code
    _save(data)


def get_last_version_check() -> str:
    """Return ISO timestamp of the last version check, or empty string."""
    return _load().get("last_version_check", "")


def set_last_version_check(timestamp: str) -> None:
    """Persist *timestamp* as the time of the last version check."""
    data = _load()
    data["last_version_check"] = timestamp
    _save(data)


def get_last_known_version() -> str:
    """Return the last fetched GitHub release tag, or empty string."""
    return _load().get("last_known_version", "")


def set_last_known_version(tag: str) -> None:
    """Persist *tag* as the last known GitHub release tag."""
    data = _load()
    data["last_known_version"] = tag
    _save(data)


def get_debug_logging() -> bool:
    """Return whether debug logging is enabled, defaulting to False."""
    return bool(_load().get("debug_logging", False))


def set_debug_logging(enabled: bool) -> None:
    """Persist debug logging enabled state."""
    data = _load()
    data["debug_logging"] = enabled
    _save(data)


def get_calibration_x() -> float:
    """Return the saved horizontal calibration offset in mm, defaulting to 0.0."""
    return float(_load().get("calibration_x_mm", 0.0))


def set_calibration_x(value: float) -> None:
    """Persist horizontal calibration offset in mm."""
    data = _load()
    data["calibration_x_mm"] = value
    _save(data)


def get_calibration_y() -> float:
    """Return the saved vertical calibration offset in mm, defaulting to 0.0."""
    return float(_load().get("calibration_y_mm", 0.0))


def set_calibration_y(value: float) -> None:
    """Persist vertical calibration offset in mm."""
    data = _load()
    data["calibration_y_mm"] = value
    _save(data)


def get_show_print_hint() -> bool:
    """Return whether the print-settings hint dialog should be shown, defaulting to True."""
    return bool(_load().get("show_print_hint", True))


def set_show_print_hint(value: bool) -> None:
    """Persist whether to show the print-settings hint dialog."""
    data = _load()
    data["show_print_hint"] = value
    _save(data)


def get_save_to_collection() -> bool:
    """Return the last state of "Also save to collection", defaulting to True."""
    return bool(_load().get("save_to_collection", True))


def set_save_to_collection(value: bool) -> None:
    """Persist the state of "Also save to collection" (queue editor, LOCAL mode)."""
    data = _load()
    data["save_to_collection"] = value
    _save(data)


# ── Window geometry and table header state ────────────────────────────────────
# Keys: "main_window", "collection_dialog", "review_dialog", "discogs_dialog",
# "settings_dialog". The values are opaque Qt blobs, stored as base64 strings.

def _decode(value: object) -> bytes | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return base64.b64decode(value.encode("ascii"), validate=True)
    except (binascii.Error, ValueError):
        return None


def _encode(data: bytes) -> str:
    return base64.b64encode(bytes(data)).decode("ascii")


def get_window_geometry(key: str) -> bytes | None:
    """Return the saved saveGeometry() blob of window *key*, or None (unset / invalid)."""
    stored = _load().get("window_geometry")
    return _decode(stored.get(key)) if isinstance(stored, dict) else None


def set_window_geometry(key: str, data: bytes) -> None:
    """Persist the saveGeometry() blob *data* of window *key*."""
    settings = _load()
    stored = settings.get("window_geometry")
    if not isinstance(stored, dict):
        stored = {}
    stored[key] = _encode(data)
    settings["window_geometry"] = stored
    _save(settings)


def get_header_state(key: str) -> tuple[int, bytes] | None:
    """Return (column count, saveState() blob) of the table header in window *key*.

    None if nothing (or something invalid) is stored.
    """
    stored = _load().get("header_state")
    entry = stored.get(key) if isinstance(stored, dict) else None
    if not isinstance(entry, dict):
        return None
    columns = entry.get("columns")
    state = _decode(entry.get("state"))
    if not isinstance(columns, int) or isinstance(columns, bool) or state is None:
        return None
    return columns, state


def set_header_state(key: str, columns: int, data: bytes) -> None:
    """Persist the header saveState() blob *data* (of a table with *columns* columns)."""
    settings = _load()
    stored = settings.get("header_state")
    if not isinstance(stored, dict):
        stored = {}
    stored[key] = {"columns": columns, "state": _encode(data)}
    settings["header_state"] = stored
    _save(settings)

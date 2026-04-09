"""
Persistent application settings stored as JSON.

Currently stores:
  watermark_path    — absolute path string, or null
  data_source_mode  — "local" or "discogs"
  theme             — "auto", "dark", or "light"
"""

from __future__ import annotations

import json
from pathlib import Path

from modules.data_source import DataSourceMode

_SETTINGS_FILE = Path(__file__).parent / "settings.json"


def _load() -> dict:
    if _SETTINGS_FILE.exists():
        try:
            return json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save(data: dict) -> None:
    _SETTINGS_FILE.write_text(
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

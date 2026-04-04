"""
Persistent application settings stored as JSON.

Currently stores:
  watermark_path  — absolute path string, or null
"""

from __future__ import annotations

import json
from pathlib import Path

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

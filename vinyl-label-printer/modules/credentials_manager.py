"""
Secure credential storage for Discogs API access.

Credentials are kept in config/credentials.json (never committed).
On first run the file is created from credentials.example.json.
After each write the file permissions are set to 0o600 (owner r/w only).
On Windows os.chmod is accepted by the OS but has no effect — acceptable
for a single-user desktop app.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

_CONFIG_DIR = Path(__file__).parent.parent / "config"
_CREDENTIALS_FILE = _CONFIG_DIR / "credentials.json"
_EXAMPLE_FILE = _CONFIG_DIR / "credentials.example.json"

_EMPTY: dict = {"discogs_username": "", "discogs_token": ""}


class CredentialsManager:
    """Load, save and clear Discogs credentials from credentials.json."""

    def load(self) -> dict:
        """Return credentials dict with keys discogs_username / discogs_token.

        If credentials.json does not exist it is created from the example
        template (or from scratch if the template is also missing).
        """
        if not _CREDENTIALS_FILE.exists():
            if _EXAMPLE_FILE.exists():
                data = json.loads(_EXAMPLE_FILE.read_text(encoding="utf-8"))
            else:
                data = dict(_EMPTY)
            self._write(data)
        try:
            return json.loads(_CREDENTIALS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return dict(_EMPTY)

    def save(self, username: str, token: str) -> None:
        """Persist username and token, then restrict file to owner r/w."""
        self._write({"discogs_username": username, "discogs_token": token})

    def are_valid(self) -> bool:
        """Return True if both fields are non-empty — no API call is made."""
        data = self.load()
        return bool(data.get("discogs_username")) and bool(data.get("discogs_token"))

    def clear(self) -> None:
        """Overwrite credentials with empty values (logout / reset)."""
        self._write(dict(_EMPTY))

    # ── Internal ──────────────────────────────────────────────────────────────

    def _write(self, data: dict) -> None:
        _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        _CREDENTIALS_FILE.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        try:
            os.chmod(_CREDENTIALS_FILE, 0o600)
        except NotImplementedError:
            pass  # Some platforms may not support chmod

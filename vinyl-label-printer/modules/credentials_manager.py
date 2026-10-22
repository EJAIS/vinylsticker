"""
Secure credential storage for Discogs API access.

Credentials are kept in credentials.json in the user config dir (modules.paths).
On first run the file is created from credentials.example.json.
Every write replaces the file atomically with permissions 0o600 (owner r/w
only; modules.json_store). On Windows the mode has no effect — acceptable
for a single-user desktop app. An unreadable credentials.json is moved aside
(credentials.json.corrupt-…) and the app continues without credentials.
"""

from __future__ import annotations

import json

from modules.json_store import read_json, write_json
from modules.paths import get_credentials_file, resource_path

_EXAMPLE_FILE = resource_path("config/credentials.example.json")

_EMPTY: dict = {"discogs_username": "", "discogs_token": ""}


class CredentialsManager:
    """Load, save and clear Discogs credentials from credentials.json."""

    def load(self) -> dict:
        """Return credentials dict with keys discogs_username / discogs_token.

        If credentials.json does not exist it is created from the example
        template (or from scratch if the template is also missing).
        """
        credentials_file = get_credentials_file()
        existed = credentials_file.exists()
        data = read_json(credentials_file)
        if data is not None:
            return data
        if existed:
            # Moved aside (or unreadable and left alone): no credentials for now
            return dict(_EMPTY)
        if _EXAMPLE_FILE.exists():
            data = json.loads(_EXAMPLE_FILE.read_text(encoding="utf-8"))
        else:
            data = dict(_EMPTY)
        self._write(data)
        return data

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
        write_json(get_credentials_file(), data, mode=0o600)

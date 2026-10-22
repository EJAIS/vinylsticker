"""Test setup: headless Qt and throw-away user directories.

Runs before the test modules import any app code, so settings, credentials,
cache and logs written by the tests never touch the real user profile.
"""

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_USER_DIRS = Path(tempfile.mkdtemp(prefix="vinyl-label-printer-tests-"))
for _var in (
    "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME", "XDG_STATE_HOME",
    "APPDATA", "LOCALAPPDATA",
):
    os.environ[_var] = str(_USER_DIRS / _var.lower())

# Make the app packages (config, modules, ui) importable from the tests
_APP_ROOT = Path(__file__).resolve().parent.parent
if str(_APP_ROOT) not in sys.path:
    sys.path.insert(0, str(_APP_ROOT))

import pytest  # noqa: E402  (after the environment setup above)


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch) -> Path:
    """A fresh, empty data dir per test: labels.db lives here."""
    from modules import paths

    folder = tmp_path / "data"
    folder.mkdir()
    monkeypatch.setattr(paths, "get_data_dir", lambda: folder)
    return folder

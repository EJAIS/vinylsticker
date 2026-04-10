"""GitHub release version checker."""
from __future__ import annotations

import requests

from __version__ import __version__
from modules.logger import get_logger

logger = get_logger()

GITHUB_API_URL = "https://api.github.com/repos/EJAIS/vinylsticker/releases"
GITHUB_RELEASES_URL = "https://github.com/EJAIS/vinylsticker/releases"


def get_latest_version(timeout: int = 5) -> dict:
    """
    Fetch the latest release from the GitHub API (includes pre-releases).

    Returns a dict with keys:
      success (bool), latest_version (str), tag_name (str),
      release_url (str), error (str).
    On failure, only 'success' and 'error' are guaranteed to be set.
    """
    headers = {
        "User-Agent": (
            f"VinylLabelPrinter/{__version__} "
            "+https://github.com/EJAIS/vinylsticker"
        )
    }
    logger.debug(f"Version check — {GITHUB_API_URL}")
    try:
        resp = requests.get(
            GITHUB_API_URL, headers=headers, params={"per_page": 1}, timeout=timeout
        )
        if resp.status_code != 200:
            logger.error(f"Version check failed: HTTP {resp.status_code}")
            return {"success": False, "error": "api",
                    "latest_version": "", "tag_name": "", "release_url": ""}
        data = resp.json()
        if not data:
            logger.debug("Version check — no releases published yet")
            return {"success": False, "error": "no_releases",
                    "latest_version": "", "tag_name": "", "release_url": ""}
        release = data[0]
        tag = release.get("tag_name", "")
        version = tag.lstrip("v")
        logger.debug(f"Version check — {resp.status_code}, tag={tag}")
        return {
            "success": True,
            "latest_version": version,
            "tag_name": tag,
            "release_url": release.get("html_url", GITHUB_RELEASES_URL),
            "error": "",
        }
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        logger.error(f"Version check failed: {type(e).__name__}: {e}")
        return {"success": False, "error": "network",
                "latest_version": "", "tag_name": "", "release_url": ""}
    except Exception as e:
        logger.error(f"Version check failed: {type(e).__name__}: {e}")
        return {"success": False, "error": "unknown",
                "latest_version": "", "tag_name": "", "release_url": ""}


def is_update_available(latest_version: str) -> bool:
    """
    Return True if latest_version is newer than the current __version__.

    Uses tuple comparison for correct semantic versioning.
    """
    try:
        latest = tuple(int(x) for x in latest_version.split("."))
        current = tuple(int(x) for x in __version__.split("."))
        return latest > current
    except Exception:
        return False

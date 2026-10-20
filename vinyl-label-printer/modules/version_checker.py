"""GitHub release version checker."""
from __future__ import annotations

import re

import requests

from __version__ import __version__
from modules.logger import get_logger

logger = get_logger()

GITHUB_API_URL = "https://api.github.com/repos/EJAIS/vinylsticker/releases"
GITHUB_RELEASES_URL = "https://github.com/EJAIS/vinylsticker/releases"

# Plain release tag: optional "v" / "v." + MAJOR.MINOR.PATCH, nothing else.
# Tags with a pre-release suffix (e.g. "v0.4.0-rc1") do not match.
_RELEASE_TAG_RE = re.compile(r"^v?\.?(\d+)\.(\d+)\.(\d+)$", re.IGNORECASE)


def get_latest_version(timeout: int = 5) -> dict:
    """
    Fetch the newest stable release from the GitHub API.

    Releases whose tag is not a plain MAJOR.MINOR.PATCH version (pre-release
    suffixes such as "-rc1" / "-beta") are skipped.

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
            GITHUB_API_URL, headers=headers, params={"per_page": 10}, timeout=timeout
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
        release = next(
            (r for r in data if _version_tuple(r.get("tag_name", ""))), None
        )
        if release is None:
            logger.debug("Version check — no stable release found")
            return {"success": False, "error": "no_releases",
                    "latest_version": "", "tag_name": "", "release_url": ""}
        tag = release.get("tag_name", "")
        version = _normalize_version(tag)
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


def _version_tuple(version: str) -> tuple[int, int, int] | None:
    """Parse a plain release version / tag, e.g. "v.0.2.0" → (0, 2, 0).

    Returns None for anything else, including pre-release tags ("v0.4.0-rc1").
    """
    match = _RELEASE_TAG_RE.match(version.strip())
    return tuple(int(x) for x in match.groups()) if match else None


def _normalize_version(tag: str) -> str:
    """Return a plain dotted version from a release tag, e.g. "v.0.2.0" → "0.2.0"."""
    parsed = _version_tuple(tag)
    return ".".join(str(x) for x in parsed) if parsed else ""


def is_update_available(latest_version: str) -> bool:
    """
    Return True if latest_version is newer than the current __version__.

    Uses tuple comparison for correct semantic versioning.
    """
    try:
        latest = _version_tuple(latest_version)
        current = _version_tuple(__version__)
        if latest is None or current is None:
            return False   # pre-release or unparsable — never an update
        return latest > current
    except Exception:
        return False

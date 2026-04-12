"""
Discogs REST API client.

Uses a User Token for authentication (sufficient for reading own collection).
Token is passed in the Authorization header — no OAuth flow required.
"""

from __future__ import annotations

import json
import re
import time
from typing import Callable

import requests

from modules.logger import get_logger

logger = get_logger()

_ARTIST_NUM_RE = re.compile(r"\s*\(\d+\)$")


class DiscogsClient:
    """Thin wrapper around the Discogs REST API."""

    BASE_URL   = "https://api.discogs.com"
    USER_AGENT = "VinylLabelPrinter/1.0 +https://github.com/YOURNAME/vinyl-label-printer"

    def __init__(self, username: str, token: str) -> None:
        self.username = username
        self.token    = token
        self.session  = requests.Session()
        self.session.headers.update(
            {
                "User-Agent":    self.USER_AGENT,
                "Authorization": f"Discogs token={self.token}",
            }
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def verify_token(self) -> bool:
        """Return True if the token is accepted, False on 401/403.

        Raises ConnectionError on network failure so the caller can
        distinguish "wrong token" from "no internet".
        """
        try:
            resp = self.session.get(f"{self.BASE_URL}/oauth/identity", timeout=10)
        except requests.ConnectionError as exc:
            raise ConnectionError(str(exc)) from exc
        if resp.status_code in (401, 403):
            return False
        resp.raise_for_status()
        return True

    def fetch_collection(
        self,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> list[dict]:
        """Fetch all releases from the user's collection (folder 0 = all).

        Pagination is followed automatically.  1 second is slept between
        page requests to respect Discogs rate limits (60 req/min).

        progress_callback(current_page, total_pages) is called after each
        successful page fetch.

        Raises requests.HTTPError on non-2xx responses.  The caller should
        inspect .response.status_code to distinguish 401 / 429 / other.
        """
        url: str | None = (
            f"{self.BASE_URL}/users/{self.username}"
            "/collection/folders/0/releases"
        )
        params = {"per_page": 100, "sort": "added", "sort_order": "desc"}
        releases: list[dict] = []
        current_page = 0
        total_pages  = 1  # updated after first response

        while url:
            logger.debug(
                f"Discogs API — GET collection page {current_page + 1}/{total_pages}"
            )
            resp = self.session.get(url, params=params, timeout=30)
            resp.raise_for_status()
            body = resp.json()

            pagination  = body.get("pagination", {})
            total_pages = pagination.get("pages", total_pages)
            current_page += 1
            page_releases = body.get("releases", [])
            releases.extend(page_releases)

            logger.debug(
                f"Discogs API — page {current_page}/{total_pages}: "
                f"{resp.status_code}, {len(page_releases)} releases"
            )

            if progress_callback:
                progress_callback(current_page, total_pages)

            # Follow next page URL (already contains all params)
            url    = pagination.get("urls", {}).get("next")
            params = {}  # params are embedded in the next URL

            if url:
                time.sleep(1.0)

        return releases

    def filter_7inch(self, releases: list[dict]) -> list[dict]:
        """Return normalized dicts for releases that are 7" singles.

        A release qualifies when any of its format entries lists '7"' in
        the descriptions array.

        The artist name has trailing Discogs disambiguation suffixes removed,
        e.g. 'Beatles, The (2)' → 'Beatles, The'.
        """
        result: list[dict] = []
        for release in releases:
            info = release.get("basic_information", {})
            if not self._is_7inch(info):
                continue

            artists = info.get("artists") or []
            labels  = info.get("labels") or []

            artist_name = _ARTIST_NUM_RE.sub("", artists[0]["name"]) if artists else ""
            label_str   = ""
            if labels:
                lbl    = labels[0]
                catno  = lbl.get("catno", "")
                label_str = lbl.get("name", "")
                if catno and catno.upper() != "NONE":
                    label_str = f"{label_str} {catno}"

            result.append(
                {
                    "title":      info.get("title", ""),
                    "artist":     artist_name.strip(),
                    "label":      label_str.strip(),
                    "country":    info.get("country", ""),
                    "year":       int(info.get("year") or 0),
                    "side":       "",   # not available from collection API
                    "discogs_id": release.get("id", 0),
                }
            )
        return result

    # Accepted description strings that identify a 7" single.
    # Covers the ASCII straight double-quote (most common in Discogs API),
    # the Unicode right double quotation mark variant, and the double-single-quote
    # variant occasionally seen in user-submitted entries.
    _7INCH_STRINGS: frozenset[str] = frozenset(['7"', "7\u201d", "7''"])

    def normalize_for_cache(self, releases: list[dict]) -> list[dict]:
        """Normalize ALL raw API releases for SQLite cache storage.

        Unlike filter_7inch(), this includes every release (no format filter)
        and adds is_7inch / formats_json fields.  The label field stores name
        only — catalog number is intentionally omitted for cache schema clarity.
        """
        result: list[dict] = []
        for release in releases:
            info    = release.get("basic_information", {})
            formats = info.get("formats") or []
            rid     = release.get("id", 0)

            artists     = info.get("artists") or []
            artist_name = _ARTIST_NUM_RE.sub("", artists[0]["name"]) if artists else ""

            labels     = info.get("labels") or []
            label_name = labels[0].get("name", "") if labels else ""

            # Robust 7" detection: check every description string with strip()
            # to handle whitespace variants and multiple quote encodings.
            descriptions = [
                d for fmt in formats
                for d in (fmt.get("descriptions") or [])
            ]
            is_7inch = any(
                d.strip() in self._7INCH_STRINGS
                for d in descriptions
            )

            logger.debug(
                f"Release {rid}: "
                f"descriptions={descriptions}, "
                f"is_7inch={is_7inch}"
            )

            result.append({
                "discogs_id":   rid,
                "title":        info.get("title", ""),
                "artist":       artist_name.strip(),
                "label":        label_name.strip(),
                "country":      info.get("country", ""),
                "year":         int(info.get("year") or 0),
                "formats_json": json.dumps(formats),
                "is_7inch":     is_7inch,
                "date_added":   release.get("date_added", ""),
            })
        return result

    def fetch_tracklist(self, release_id: int) -> list[dict]:
        """Fetch A/B tracks for a specific release.

        Calls GET /releases/{release_id} and returns the subset of tracks
        whose position starts with 'A' or 'B'.

        Normalisation: if the result contains exactly one A-side track and one
        B-side track the position digits are stripped ('A1' → 'A', 'B1' → 'B').
        For EPs / Maxis with multiple A or B tracks the original positions are
        kept (e.g. 'A1', 'A2', 'B1', 'B2').

        Sleeps 1 second after the request to respect Discogs rate limits.

        Raises requests.HTTPError on non-2xx responses.
        Returns dict with keys:
          'tracks'  — list[dict] with 'position' (str) and 'title' (str)
          'country' — str, top-level country field from the release response
        """
        logger.debug(f"Fetching tracklist for release_id={release_id}")
        resp = self.session.get(
            f"{self.BASE_URL}/releases/{release_id}", timeout=15
        )
        resp.raise_for_status()
        body       = resp.json()
        country    = body.get("country", "")
        raw_tracks = body.get("tracklist", [])

        ab_tracks = [
            {
                "position": trk.get("position", "").strip(),
                "title":    trk.get("title", ""),
            }
            for trk in raw_tracks
            if trk.get("position", "").upper().startswith(("A", "B"))
        ]

        a_sides = [t for t in ab_tracks if t["position"].upper().startswith("A")]
        b_sides = [t for t in ab_tracks if t["position"].upper().startswith("B")]

        if len(a_sides) == 1 and len(b_sides) == 1:
            for trk in ab_tracks:
                trk["position"] = trk["position"][0].upper()  # 'A1' → 'A'

        logger.debug(
            f"Tracklist fetched: {len(ab_tracks)} tracks for release_id={release_id}"
        )
        time.sleep(1.0)
        return {"tracks": ab_tracks, "country": country}

    # ── Internal helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _is_7inch(basic_information: dict) -> bool:
        for fmt in basic_information.get("formats", []):
            if '7"' in (fmt.get("descriptions") or []):
                return True
        return False

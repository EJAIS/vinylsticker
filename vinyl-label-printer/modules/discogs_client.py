"""
Discogs REST API client.

Uses a User Token for authentication (sufficient for reading own collection).
Token is passed in the Authorization header — no OAuth flow required.
"""

from __future__ import annotations

import json
import re
import threading
import time
from typing import Callable

import requests

from modules.logger import get_logger

logger = get_logger()

_ARTIST_NUM_RE = re.compile(r"\s*\(\d+\)$")

# Minimum spacing between any two Discogs requests (limit: 60 req/min).
MIN_REQUEST_INTERVAL_S = 1.1
# HTTP 429 handling: Discogs uses a 60 s moving window.
_RATE_LIMIT_DEFAULT_WAIT_S = 60.0
_RATE_LIMIT_MAX_RETRIES    = 2


class DiscogsRequestCancelled(Exception):
    """Raised when a request or throttle wait is aborted via the cancel event."""


class DiscogsClient:
    """Thin wrapper around the Discogs REST API.

    All HTTP calls go through _request(), which throttles requests globally
    (across all instances and threads) and retries on HTTP 429.
    """

    BASE_URL   = "https://api.discogs.com"
    USER_AGENT = "VinylLabelPrinter/1.0 +https://github.com/YOURNAME/vinyl-label-printer"

    # Shared throttle state — protected by _throttle_lock
    _throttle_lock:   threading.Lock = threading.Lock()
    _last_request_ts: float          = float("-inf")   # time.monotonic() of last slot
    _blocked_until:   float          = float("-inf")   # set after a 429 response

    def __init__(
        self,
        username: str,
        token: str,
        cancel_event: threading.Event | None = None,
    ) -> None:
        self.username = username
        self.token    = token
        # A private, never-set event keeps the wait logic uniform
        self._cancel_event = cancel_event or threading.Event()
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
            resp = self._request(f"{self.BASE_URL}/oauth/identity", timeout=10)
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

        Pagination is followed automatically; request spacing is enforced
        by _request().

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
            resp = self._request(url, params=params, timeout=30)
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

        Raises requests.HTTPError on non-2xx responses.
        Returns dict with keys:
          'tracks'  — list[dict] with 'position' (str) and 'title' (str)
          'country' — str, top-level country field from the release response
        """
        logger.debug(f"Fetching tracklist for release_id={release_id}")
        resp = self._request(
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
        return {"tracks": ab_tracks, "country": country}

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _request(self, url: str, **kwargs) -> requests.Response:
        """GET *url* with global throttling and HTTP 429 retries.

        Returns the final response; callers call raise_for_status() as
        before, so a 429 that persists after all retries still surfaces as
        requests.HTTPError.  Raises DiscogsRequestCancelled if the cancel
        event is set before or during a wait.
        """
        attempt = 0
        while True:
            self._throttle()
            resp = self.session.get(url, **kwargs)
            logger.debug(
                f"Discogs API — {resp.status_code} {url} "
                f"(rate limit remaining: "
                f"{resp.headers.get('X-Discogs-Ratelimit-Remaining', '?')})"
            )
            if resp.status_code != 429 or attempt >= _RATE_LIMIT_MAX_RETRIES:
                return resp

            attempt += 1
            wait_s = self._retry_after_seconds(resp)
            logger.warning(
                f"Discogs API rate limit hit (429) — retry {attempt}/"
                f"{_RATE_LIMIT_MAX_RETRIES} in {wait_s:.0f}s"
            )
            # Block all clients, not just this one, until the window has passed
            with DiscogsClient._throttle_lock:
                DiscogsClient._blocked_until = max(
                    DiscogsClient._blocked_until, time.monotonic() + wait_s
                )

    def _throttle(self) -> None:
        """Wait until this thread may send the next request.

        A time slot is reserved under the lock; the actual wait happens
        outside of it so that it stays cancellable and does not block
        other threads from reserving their own (later) slots.
        """
        with DiscogsClient._throttle_lock:
            now  = time.monotonic()
            slot = max(
                now,
                DiscogsClient._last_request_ts + MIN_REQUEST_INTERVAL_S,
                DiscogsClient._blocked_until,
            )
            DiscogsClient._last_request_ts = slot
        self._wait(slot - now)

    def _wait(self, seconds: float) -> None:
        """Sleep for *seconds* unless the cancel event is set."""
        if self._cancel_event.wait(max(seconds, 0.0)):
            raise DiscogsRequestCancelled()

    @staticmethod
    def _retry_after_seconds(resp: requests.Response) -> float:
        try:
            return max(float(resp.headers["Retry-After"]), 0.0)
        except (KeyError, TypeError, ValueError):
            return _RATE_LIMIT_DEFAULT_WAIT_S

    @staticmethod
    def _is_7inch(basic_information: dict) -> bool:
        for fmt in basic_information.get("formats", []):
            if '7"' in (fmt.get("descriptions") or []):
                return True
        return False

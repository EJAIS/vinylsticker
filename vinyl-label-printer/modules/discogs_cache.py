"""
SQLite-based local cache for Discogs collection data.

Enforces Discogs API Terms of Use: cached data older than 6 hours
must never be displayed to users.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from modules.logger import get_logger

logger = get_logger()

DB_PATH             = Path(__file__).parent.parent / "data" / "discogs_cache.db"
CACHE_MAX_AGE_HOURS = 6


class DiscogsCache:
    """
    SQLite-based local cache for Discogs collection data.
    Enforces Discogs API ToU: data older than 6 hours is invalid.
    """

    def __init__(self) -> None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _get_connection(self) -> sqlite3.Connection:
        """Open and return a new SQLite connection. Never store this as an instance var."""
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Create tables and indexes if they don't exist."""
        logger.debug(f"Cache DB path: {DB_PATH}")
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS releases (
                    discogs_id          INTEGER PRIMARY KEY,
                    title               TEXT NOT NULL,
                    artist              TEXT NOT NULL,
                    label               TEXT DEFAULT '',
                    country             TEXT DEFAULT '',
                    year                INTEGER DEFAULT 0,
                    formats_json        TEXT DEFAULT '[]',
                    is_7inch            BOOLEAN DEFAULT FALSE,
                    tracklist_json      TEXT DEFAULT '[]',
                    tracklist_fetched   BOOLEAN DEFAULT FALSE,
                    date_added          TEXT DEFAULT '',
                    updated_at          TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS cache_meta (
                    key     TEXT PRIMARY KEY,
                    value   TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_is_7inch
                    ON releases(is_7inch);
                CREATE INDEX IF NOT EXISTS idx_artist
                    ON releases(artist);
            """)
            # Migration: add date_added column to existing DBs that predate this field
            try:
                conn.execute(
                    "ALTER TABLE releases ADD COLUMN date_added TEXT DEFAULT ''"
                )
                logger.info("DB migration: added date_added column")
            except sqlite3.OperationalError:
                pass  # Column already exists — normal on fresh DBs and after first migration
        logger.debug("Cache DB initialized — tables ready")

    # ── Meta / Status ──────────────────────────────────────────────────────────

    def get_cached_at(self) -> datetime | None:
        """Returns UTC datetime of last successful pull, or None."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT value FROM cache_meta WHERE key='cached_at'"
            ).fetchone()
            if row:
                return datetime.fromisoformat(row["value"])
        return None

    def get_cache_status(self) -> dict:
        """
        Returns cache status dict:
        {
            "has_cache":    bool,
            "is_valid":     bool,   # False if > 6 hours old
            "cached_at":    datetime | None,
            "age_hours":    float | None,
            "total_items":  int,
            "items_7inch":  int,
            "username":     str,
        }
        """
        cached_at = self.get_cached_at()
        if not cached_at:
            status = {
                "has_cache":   False,
                "is_valid":    False,
                "cached_at":   None,
                "age_hours":   None,
                "total_items": 0,
                "items_7inch": 0,
                "username":    "",
            }
            logger.debug(
                f"Cache status: has=False, valid=False, age=None, 7inch=0"
            )
            return status

        age       = datetime.utcnow() - cached_at
        age_hours = round(age.total_seconds() / 3600, 1)
        is_valid  = age < timedelta(hours=CACHE_MAX_AGE_HOURS)

        with self._get_connection() as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM releases"
            ).fetchone()[0]
            items_7inch = conn.execute(
                "SELECT COUNT(*) FROM releases WHERE is_7inch=TRUE"
            ).fetchone()[0]
            username_row = conn.execute(
                "SELECT value FROM cache_meta WHERE key='username'"
            ).fetchone()
            username = username_row["value"] if username_row else ""

        status = {
            "has_cache":   True,
            "is_valid":    is_valid,
            "cached_at":   cached_at,
            "age_hours":   age_hours,
            "total_items": total,
            "items_7inch": items_7inch,
            "username":    username,
        }
        logger.debug(
            f"Cache status: has={status['has_cache']}, "
            f"valid={status['is_valid']}, "
            f"age={status['age_hours']}h, "
            f"7inch={status['items_7inch']}"
        )

        # Diagnostic samples — visible only in debug mode
        with self._get_connection() as conn:
            sample = conn.execute(
                "SELECT discogs_id, title, is_7inch, formats_json "
                "FROM releases LIMIT 5"
            ).fetchall()
            fetched_count = conn.execute(
                "SELECT COUNT(*) FROM releases "
                "WHERE tracklist_fetched = 1"
            ).fetchone()[0]
            not_fetched = conn.execute(
                "SELECT COUNT(*) FROM releases "
                "WHERE is_7inch = 1 "
                "AND (tracklist_fetched = 0 OR tracklist_fetched IS NULL)"
            ).fetchone()[0]

        for row in sample:
            logger.debug(
                f"DB sample: id={row['discogs_id']}, "
                f"title={row['title'][:30]!r}, "
                f"is_7inch={row['is_7inch']}, "
                f"formats={row['formats_json'][:80]}"
            )
        logger.debug(
            f"Tracklist Cache: {fetched_count} gecacht, "
            f"{not_fetched} × 7\" ausstehend"
        )

        return status

    # ── Read ───────────────────────────────────────────────────────────────────

    def get_7inch_releases(self) -> list[dict]:
        """
        Returns all 7" releases from cache as list of dicts.
        IMPORTANT: Caller must verify cache is_valid before calling.
        Raises RuntimeError if cache is expired.
        """
        status = self.get_cache_status()
        if not status["is_valid"]:
            logger.error(
                "Cache read blocked: data > 6h old "
                "(Discogs API ToU violation prevention)"
            )
            raise RuntimeError(
                "Cache expired (> 6h) — reload required per "
                "Discogs API Terms of Use"
            )

        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM releases WHERE is_7inch=1 "
                "ORDER BY date_added DESC, artist, title"
            ).fetchall()

        logger.debug(f"Loading {len(rows)} 7\" releases from cache")
        return [dict(row) for row in rows]

    def get_release(self, discogs_id: int) -> dict | None:
        """Returns single release by discogs_id, or None."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM releases WHERE discogs_id=?",
                (discogs_id,)
            ).fetchone()
        return dict(row) if row else None

    def get_pending_tracklist_ids(self) -> list[int]:
        """
        Returns discogs_ids of 7" releases without a cached tracklist.
        Explicitly includes rows where tracklist_fetched is NULL or 0/FALSE.
        """
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT discogs_id FROM releases
                WHERE is_7inch = 1
                AND (tracklist_fetched = 0
                     OR tracklist_fetched IS NULL)
            """).fetchall()
            total_7inch = conn.execute(
                "SELECT COUNT(*) FROM releases WHERE is_7inch = 1"
            ).fetchone()[0]
        ids = [int(row["discogs_id"]) for row in rows]
        already_cached = total_7inch - len(ids)
        logger.debug(
            f"Pending tracklists: {len(ids)} ausstehend, "
            f"{already_cached} bereits gecacht "
            f"(von {total_7inch} × 7\" gesamt)"
        )
        return ids

    def is_date_added_populated(self) -> bool:
        """Returns True if at least one release has a non-empty date_added value.

        Used to detect whether an existing cache was built before date_added
        was introduced and needs a full reload.
        """
        with self._get_connection() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM releases WHERE date_added != ''"
            ).fetchone()[0]
        return count > 0

    # ── Write ──────────────────────────────────────────────────────────────────

    def sync_releases(self, releases: list[dict], username: str) -> dict:
        """
        Full sync: compare API response with local cache.
        - Add new releases
        - Update changed releases (title, label, country, year, artist)
        - Delete removed releases (in cache but no longer in API)

        Does NOT overwrite tracklist_json / tracklist_fetched on update.

        Returns sync report:
        {
            "added":     int,
            "updated":   int,
            "removed":   int,
            "unchanged": int,
        }
        """
        # Deduplicate by discogs_id — the API can occasionally return the same
        # release on multiple pages.  Keep the first occurrence.
        seen: set[int] = set()
        unique: list[dict] = []
        for r in releases:
            rid = r["discogs_id"]
            if rid not in seen:
                seen.add(rid)
                unique.append(r)
        if len(unique) < len(releases):
            logger.debug(
                f"Deduplicated API releases: {len(releases)} → {len(unique)} "
                f"({len(releases) - len(unique)} duplicates removed)"
            )
        releases = unique

        logger.info(
            f"Starting cache sync for @{username} "
            f"— {len(releases)} releases from API"
        )

        now_iso = datetime.utcnow().isoformat()
        stats   = {"added": 0, "updated": 0, "removed": 0, "unchanged": 0}
        api_ids = {r["discogs_id"] for r in releases}

        with self._get_connection() as conn:
            existing_rows = conn.execute(
                "SELECT discogs_id, title, artist, label, country, year "
                "FROM releases"
            ).fetchall()
            existing = {row["discogs_id"]: dict(row) for row in existing_rows}
            logger.debug(f"Existing cache entries: {len(existing)}")

            for release in releases:
                rid = release["discogs_id"]

                if rid not in existing:
                    conn.execute("""
                        INSERT INTO releases (
                            discogs_id, title, artist, label,
                            country, year, formats_json, is_7inch,
                            tracklist_json, tracklist_fetched,
                            date_added, updated_at)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                    """, (
                        rid,
                        release["title"],
                        release["artist"],
                        release.get("label", ""),
                        release.get("country", ""),
                        release.get("year", 0),
                        release.get("formats_json", "[]"),
                        release.get("is_7inch", False),
                        "[]",
                        False,
                        release.get("date_added", ""),
                        now_iso,
                    ))
                    stats["added"] += 1
                    logger.debug(f"Cache ADD: discogs_id={rid} '{release['title']}'")

                else:
                    cached = existing[rid]
                    changed_fields = []
                    if cached["title"]   != release["title"]:
                        changed_fields.append("title")
                    if cached["artist"]  != release["artist"]:
                        changed_fields.append("artist")
                    if cached["label"]   != release.get("label", ""):
                        changed_fields.append("label")
                    if cached["country"] != release.get("country", ""):
                        changed_fields.append("country")
                    if cached["year"]    != release.get("year", 0):
                        changed_fields.append("year")

                    if changed_fields:
                        conn.execute("""
                            UPDATE releases SET
                                title=?, artist=?, label=?,
                                country=?, year=?, formats_json=?,
                                is_7inch=?, date_added=?, updated_at=?
                            WHERE discogs_id=?
                        """, (
                            release["title"],
                            release["artist"],
                            release.get("label", ""),
                            release.get("country", ""),
                            release.get("year", 0),
                            release.get("formats_json", "[]"),
                            release.get("is_7inch", False),
                            release.get("date_added", ""),
                            now_iso,
                            rid,
                        ))
                        stats["updated"] += 1
                        logger.debug(
                            f"Cache UPDATE: discogs_id={rid} "
                            f"(changed: {changed_fields})"
                        )
                    else:
                        stats["unchanged"] += 1
                        logger.debug(f"Cache UNCHANGED: discogs_id={rid}")

            # Releases no longer in API — delete them
            removed_ids = set(existing.keys()) - api_ids
            for rid in removed_ids:
                logger.debug(
                    f"Cache REMOVE: discogs_id={rid} (no longer in collection)"
                )
            if removed_ids:
                placeholders = ",".join("?" * len(removed_ids))
                conn.execute(
                    f"DELETE FROM releases WHERE discogs_id IN ({placeholders})",
                    list(removed_ids)
                )
                stats["removed"] += len(removed_ids)

            # Update meta
            conn.execute(
                "INSERT OR REPLACE INTO cache_meta VALUES ('cached_at', ?)",
                (now_iso,)
            )
            conn.execute(
                "INSERT OR REPLACE INTO cache_meta VALUES ('username', ?)",
                (username,)
            )
            conn.execute(
                "INSERT OR REPLACE INTO cache_meta VALUES ('total_items', ?)",
                (str(len(releases)),)
            )

        logger.info(
            f"Sync complete: +{stats['added']} new, "
            f"~{stats['updated']} updated, "
            f"-{stats['removed']} removed, "
            f"={stats['unchanged']} unchanged"
        )
        return stats

    def update_tracklist(self, discogs_id: int, tracklist: list[dict]) -> None:
        """Saves fetched tracklist for a release."""
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE releases SET
                    tracklist_json    = ?,
                    tracklist_fetched = 1,
                    updated_at        = ?
                WHERE discogs_id = ?
            """, (
                json.dumps(tracklist, ensure_ascii=False),
                datetime.utcnow().isoformat(),
                int(discogs_id),
            ))
            # Verify the write was applied
            row = conn.execute(
                "SELECT tracklist_fetched FROM releases WHERE discogs_id = ?",
                (discogs_id,)
            ).fetchone()
            if row and row["tracklist_fetched"]:
                logger.debug(
                    f"Tracklist gespeichert: discogs_id={discogs_id} "
                    f"({len(tracklist)} Tracks) ✓"
                )
            else:
                logger.error(
                    f"Tracklist NICHT gespeichert: discogs_id={discogs_id} "
                    f"— DB update fehlgeschlagen!"
                )

    def debug_tracklist_status(self) -> None:
        """Log detailed tracklist cache status. Call once after dialog opens."""
        with self._get_connection() as conn:
            fetched = conn.execute("""
                SELECT COUNT(*) FROM releases
                WHERE is_7inch = 1 AND tracklist_fetched = 1
            """).fetchone()[0]

            not_fetched = conn.execute("""
                SELECT COUNT(*) FROM releases
                WHERE is_7inch = 1
                AND (tracklist_fetched = 0 OR tracklist_fetched IS NULL)
            """).fetchone()[0]

            sample_missing = conn.execute("""
                SELECT discogs_id, title, tracklist_fetched
                FROM releases
                WHERE is_7inch = 1
                AND (tracklist_fetched = 0 OR tracklist_fetched IS NULL)
                LIMIT 5
            """).fetchall()

            sample_cached = conn.execute("""
                SELECT discogs_id, title, tracklist_fetched,
                       length(tracklist_json) as json_len
                FROM releases
                WHERE is_7inch = 1 AND tracklist_fetched = 1
                LIMIT 5
            """).fetchall()

        logger.debug("=== Tracklist Cache Status ===")
        logger.debug(f"Gecacht: {fetched} | Ausstehend: {not_fetched}")
        if sample_missing:
            logger.debug("Sample NICHT gecacht:")
            for row in sample_missing:
                logger.debug(
                    f"  id={row['discogs_id']}, "
                    f"title={row['title'][:40]!r}, "
                    f"fetched={row['tracklist_fetched']}"
                )
        if sample_cached:
            logger.debug("Sample gecacht:")
            for row in sample_cached:
                logger.debug(
                    f"  id={row['discogs_id']}, "
                    f"title={row['title'][:40]!r}, "
                    f"json_len={row['json_len']}"
                )

    def clear(self) -> None:
        """Wipes all cached data."""
        with self._get_connection() as conn:
            conn.executescript("""
                DELETE FROM releases;
                DELETE FROM cache_meta;
            """)
        logger.warning("Cache CLEARED — all local Discogs data deleted")

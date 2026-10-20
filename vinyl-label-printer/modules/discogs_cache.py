"""
SQLite-based local cache for Discogs collection data.

Enforces Discogs API Terms of Use: cached data older than 6 hours
must never be displayed to users.  Two groups of fields with separate
freshness are stored per release:

  Collection fields — title, artist, label, catno, year, formats_json,
                      is_7inch, date_added.  Refreshed by every full sync;
                      validity is tracked by cache_meta.cached_at.
  Detail fields     — country, tracklist_json, details_fetched_at.
                      Fetched on demand from /releases/{id}; each release
                      has its own TTL via details_fetched_at.

The legacy tracklist_fetched column is kept in the table but no longer used.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

from modules.logger import get_logger

logger = get_logger()

DB_PATH             = Path(__file__).parent.parent / "data" / "discogs_cache.db"
CACHE_MAX_AGE_HOURS = 6

# Fields from the collection endpoint — refreshed by every full sync
_COLLECTION_FIELDS = (
    "title", "artist", "label", "catno", "year",
    "formats_json", "is_7inch", "date_added",
)


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

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        """Yield a connection; commit (or roll back on error) and always close it.

        sqlite3's own "with conn" only manages the transaction — it never
        closes the connection.
        """
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Create tables and indexes if they don't exist."""
        logger.debug(f"Cache DB path: {DB_PATH}")
        with self._connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS releases (
                    discogs_id          INTEGER PRIMARY KEY,
                    title               TEXT NOT NULL,
                    artist              TEXT NOT NULL,
                    label               TEXT DEFAULT '',
                    catno               TEXT DEFAULT '',
                    country             TEXT DEFAULT '',
                    year                INTEGER DEFAULT 0,
                    formats_json        TEXT DEFAULT '[]',
                    is_7inch            BOOLEAN DEFAULT FALSE,
                    tracklist_json      TEXT DEFAULT '[]',
                    tracklist_fetched   BOOLEAN DEFAULT FALSE,
                    date_added          TEXT DEFAULT '',
                    details_fetched_at  TEXT DEFAULT '',
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
            # Migrations: add columns to existing DBs that predate these fields
            self._add_column(conn, "date_added")
            catno_added = self._add_column(conn, "catno")
            self._add_column(conn, "details_fetched_at")
            if catno_added:
                # Force the "load required" state so the next sync fills catno
                conn.execute("DELETE FROM cache_meta WHERE key='cached_at'")
                logger.info("DB migration: cache invalidated to populate catno")
        logger.debug("Cache DB initialized — tables ready")

    @staticmethod
    def _add_column(conn: sqlite3.Connection, name: str) -> bool:
        """Add a TEXT column with default '' — return True if it was newly added."""
        try:
            conn.execute(f"ALTER TABLE releases ADD COLUMN {name} TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            return False  # Column already exists — normal on fresh DBs
        logger.info(f"DB migration: added {name} column")
        return True

    @staticmethod
    def _parse_utc(value: str) -> datetime:
        """Parse an ISO timestamp; naive values (older caches) are treated as UTC."""
        dt = datetime.fromisoformat(value)
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt

    # ── Meta / Status ──────────────────────────────────────────────────────────

    def get_cached_at(self) -> datetime | None:
        """Returns UTC datetime of last successful pull, or None."""
        with self._connection() as conn:
            row = conn.execute(
                "SELECT value FROM cache_meta WHERE key='cached_at'"
            ).fetchone()
        if not row:
            return None
        return self._parse_utc(row["value"])

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
                "Cache status: has=False, valid=False, age=None, 7inch=0"
            )
            return status

        age       = datetime.now(timezone.utc) - cached_at
        age_hours = round(age.total_seconds() / 3600, 1)
        is_valid  = age < timedelta(hours=CACHE_MAX_AGE_HOURS)

        with self._connection() as conn:
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
        with self._connection() as conn:
            sample = conn.execute(
                "SELECT discogs_id, title, is_7inch, formats_json "
                "FROM releases LIMIT 5"
            ).fetchall()

        for row in sample:
            logger.debug(
                f"DB sample: id={row['discogs_id']}, "
                f"title={row['title'][:30]!r}, "
                f"is_7inch={row['is_7inch']}, "
                f"formats={row['formats_json'][:80]}"
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

        with self._connection() as conn:
            rows = conn.execute(
                "SELECT * FROM releases WHERE is_7inch=1 "
                "ORDER BY date_added DESC, artist, title"
            ).fetchall()

        logger.debug(f"Loading {len(rows)} 7\" releases from cache")
        return [dict(row) for row in rows]

    def get_release(self, discogs_id: int) -> dict | None:
        """Returns single release by discogs_id, or None."""
        with self._connection() as conn:
            row = conn.execute(
                "SELECT * FROM releases WHERE discogs_id=?",
                (discogs_id,)
            ).fetchone()
        return dict(row) if row else None

    def is_date_added_populated(self) -> bool:
        """Returns True if at least one release has a non-empty date_added value.

        Used to detect whether an existing cache was built before date_added
        was introduced and needs a full reload.
        """
        with self._connection() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM releases WHERE date_added != ''"
            ).fetchone()[0]
        return count > 0

    # ── Write ──────────────────────────────────────────────────────────────────

    def sync_releases(self, releases: list[dict], username: str) -> dict:
        """
        Full sync: compare API response with local cache.
        - Add new releases (detail fields left empty)
        - Update changed releases — any collection field differs
          (title, artist, label, catno, year, formats_json, is_7inch,
          date_added); only collection fields are written
        - Delete removed releases (in cache but no longer in API)

        Never touches the detail fields (country, tracklist_json,
        details_fetched_at) of existing releases.

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

        now_iso = datetime.now(timezone.utc).isoformat()
        stats   = {"added": 0, "updated": 0, "removed": 0, "unchanged": 0}
        api_ids = {r["discogs_id"] for r in releases}

        with self._connection() as conn:
            existing_rows = conn.execute(
                f"SELECT discogs_id, {', '.join(_COLLECTION_FIELDS)} FROM releases"
            ).fetchall()
            existing = {row["discogs_id"]: dict(row) for row in existing_rows}
            logger.debug(f"Existing cache entries: {len(existing)}")

            for release in releases:
                rid = release["discogs_id"]

                values = self._collection_values(release)

                if rid not in existing:
                    conn.execute(f"""
                        INSERT INTO releases (
                            discogs_id, {', '.join(_COLLECTION_FIELDS)},
                            country, tracklist_json, details_fetched_at,
                            updated_at)
                        VALUES ({', '.join('?' * (len(_COLLECTION_FIELDS) + 5))})
                    """, (rid, *values.values(), "", "[]", "", now_iso))
                    stats["added"] += 1
                    logger.debug(f"Cache ADD: discogs_id={rid} '{release['title']}'")

                else:
                    cached = existing[rid]
                    changed_fields = [
                        field for field, value in values.items()
                        if cached[field] != value
                    ]

                    if changed_fields:
                        assignments = ", ".join(f"{f}=?" for f in _COLLECTION_FIELDS)
                        conn.execute(
                            f"UPDATE releases SET {assignments}, updated_at=? "
                            "WHERE discogs_id=?",
                            (*values.values(), now_iso, rid),
                        )
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

    @staticmethod
    def _collection_values(release: dict) -> dict:
        """Return the collection fields of a normalized release, in DB form."""
        return {
            "title":        release["title"],
            "artist":       release["artist"],
            "label":        release.get("label", ""),
            "catno":        release.get("catno", ""),
            "year":         release.get("year", 0),
            "formats_json": release.get("formats_json", "[]"),
            "is_7inch":     int(bool(release.get("is_7inch", False))),
            "date_added":   release.get("date_added", ""),
        }

    def get_details(self, discogs_id: int) -> dict | None:
        """Return {"tracks": list, "country": str} if fresh details are cached.

        Details older than CACHE_MAX_AGE_HOURS (Discogs API ToU) or never
        fetched yield None — the caller must fetch them from the API.
        """
        with self._connection() as conn:
            row = conn.execute(
                "SELECT tracklist_json, country, details_fetched_at "
                "FROM releases WHERE discogs_id=?",
                (int(discogs_id),),
            ).fetchone()
        if not row or not row["details_fetched_at"]:
            return None
        age = datetime.now(timezone.utc) - self._parse_utc(row["details_fetched_at"])
        if age >= timedelta(hours=CACHE_MAX_AGE_HOURS):
            logger.debug(
                f"Details expired: discogs_id={discogs_id} "
                f"(age={age.total_seconds() / 3600:.1f}h)"
            )
            return None
        return {
            "tracks":  json.loads(row["tracklist_json"] or "[]"),
            "country": row["country"] or "",
        }

    def save_details(self, discogs_id: int, tracks: list[dict], country: str) -> None:
        """Store release details (tracklist + country) with the current timestamp."""
        with self._connection() as conn:
            conn.execute("""
                UPDATE releases SET
                    tracklist_json     = ?,
                    country            = ?,
                    details_fetched_at = ?
                WHERE discogs_id = ?
            """, (
                json.dumps(tracks, ensure_ascii=False),
                country or "",
                datetime.now(timezone.utc).isoformat(),
                int(discogs_id),
            ))
        logger.debug(
            f"Details saved: discogs_id={discogs_id} "
            f"({len(tracks)} tracks, country={country!r})"
        )

    def clear(self) -> None:
        """Wipes all cached data."""
        with self._connection() as conn:
            conn.executescript("""
                DELETE FROM releases;
                DELETE FROM cache_meta;
            """)
        logger.warning("Cache CLEARED — all local Discogs data deleted")

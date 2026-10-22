"""
Print queue storage in labels.db (SQLite) — the only code that talks to labels.db.

Every public function opens a short-lived connection, runs in exactly one
transaction (BEGIN IMMEDIATE … COMMIT, ROLLBACK on any error) and closes the
connection again. The app is single-user; the default rollback journal is used
(no WAL), so labels.db is a plain single file that can be backed up by copying.

Schema versions
---------------
PRAGMA user_version holds the number of applied entries of _MIGRATIONS. Each
connection applies the missing ones in order, inside its transaction. New
versions append an entry and never change an existing one; they must keep the
print_queue table readable for older app versions (add tables / columns only).

Version 1
  print_queue  one row per label, ordered by the explicit position column
  meta         key/value pairs, e.g. the xlsx migration marker
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import datetime, timezone

from modules import paths
from modules.logger import get_logger
from modules.records import LabelRecord, normalise_side

logger = get_logger()

# Values of print_queue.source
SOURCE_MANUAL = "manual"
SOURCE_CSV = "csv"
SOURCE_DISCOGS = "discogs"
SOURCE_XLSX = "xlsx-migration"

# meta key written by the one-time migration from database.xlsx
META_XLSX_MIGRATED = "xlsx_migrated"

_MIGRATIONS: tuple[tuple[str, ...], ...] = (
    # 1 — print queue + meta
    (
        """
        CREATE TABLE print_queue (
            id         INTEGER PRIMARY KEY,
            position   INTEGER NOT NULL,
            title      TEXT    NOT NULL CHECK (title <> ''),
            artist     TEXT    NOT NULL DEFAULT '',
            label      TEXT    NOT NULL DEFAULT '',
            country    TEXT    NOT NULL DEFAULT '',
            year       TEXT    NOT NULL DEFAULT '',
            side       TEXT    NOT NULL CHECK (side IN ('A', 'B')),
            catno      TEXT    NOT NULL DEFAULT '',
            source     TEXT    NOT NULL DEFAULT 'manual',
            created_at TEXT    NOT NULL,
            updated_at TEXT    NOT NULL
        )
        """,
        "CREATE INDEX print_queue_position ON print_queue (position)",
        """
        CREATE TABLE meta (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """,
    ),
)

SCHEMA_VERSION = len(_MIGRATIONS)

_DATA_COLUMNS = ("title", "artist", "label", "country", "year", "side", "catno")
_SELECT_COLUMNS = ", ".join(("id",) + _DATA_COLUMNS + ("source",))

_warned_newer_schema = False


# ── Connection handling ───────────────────────────────────────────────────────

@contextmanager
def _transaction() -> Iterator[sqlite3.Connection]:
    """Open labels.db, bring the schema up to date, yield inside one transaction."""
    # isolation_level=None: no implicit transactions, BEGIN/COMMIT are explicit
    conn = sqlite3.connect(str(paths.get_labels_db_file()), timeout=10, isolation_level=None)
    try:
        conn.execute("BEGIN IMMEDIATE")
        try:
            _ensure_schema(conn)
            yield conn
            conn.execute("COMMIT")
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()


def _ensure_schema(conn: sqlite3.Connection) -> None:
    """Apply the missing _MIGRATIONS; runs inside the caller's transaction."""
    global _warned_newer_schema
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if version > SCHEMA_VERSION:
        if not _warned_newer_schema:
            logger.warning(
                f"labels.db has schema version {version}, this app knows up to "
                f"{SCHEMA_VERSION} — using the tables it knows"
            )
            _warned_newer_schema = True
        return
    for index in range(version, SCHEMA_VERSION):
        for statement in _MIGRATIONS[index]:
            conn.execute(statement)
        # PRAGMA takes no parameters; index is an int from range()
        conn.execute(f"PRAGMA user_version = {index + 1}")
        logger.info(f"labels.db schema migrated to version {index + 1}")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _values(record: LabelRecord) -> tuple[str, ...]:
    """The data column values of *record*, side normalised to "A" / "B".

    Raises:
        ValueError: if the title is empty.
    """
    if not (record.title or "").strip():
        raise ValueError("A print queue entry needs a title")
    return (
        record.title,
        record.artist or "",
        record.label or "",
        record.country or "",
        record.year or "",
        normalise_side(record.side),
        record.catno or "",
    )


def _insert(
    conn: sqlite3.Connection,
    position: int,
    values: tuple[str, ...],
    source: str,
    now: str,
) -> None:
    conn.execute(
        f"INSERT INTO print_queue (position, {', '.join(_DATA_COLUMNS)}, "
        "source, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (position, *values, source, now, now),
    )


# ── Public API ────────────────────────────────────────────────────────────────

def load_queue() -> list[LabelRecord]:
    """Return the print queue in its stored order (with id and source)."""
    with _transaction() as conn:
        rows = conn.execute(
            f"SELECT {_SELECT_COLUMNS} FROM print_queue ORDER BY position, id"
        ).fetchall()
    records = [
        LabelRecord(
            title=row[1], artist=row[2], label=row[3], country=row[4],
            year=row[5], side=row[6], catno=row[7], id=row[0], source=row[8],
        )
        for row in rows
    ]
    logger.info(f"Print queue loaded: {len(records)} records")
    return records


def queue_count() -> int:
    """Number of entries in the print queue."""
    with _transaction() as conn:
        return conn.execute("SELECT COUNT(*) FROM print_queue").fetchone()[0]


def replace_queue(records: Sequence[LabelRecord], source: str = SOURCE_MANUAL) -> None:
    """Make *records* the whole print queue, in this order.

    A record whose id is in the queue keeps that row (id, source, created_at;
    updated_at changes only if its data changed). Records without a known id
    are new rows with their own source, or *source* if they have none. Queue
    rows that are not in *records* are deleted.

    Raises:
        ValueError: if a record has an empty title (nothing is written).
    """
    rows = [(record, _values(record)) for record in records]
    with _transaction() as conn:
        existing = {
            row[0]: tuple(row[1:])
            for row in conn.execute(f"SELECT id, {', '.join(_DATA_COLUMNS)} FROM print_queue")
        }
        kept: set[int] = set()
        for record, _ in rows:
            # A duplicated row may carry the id of its original: only the first keeps it
            if record.id in existing and record.id not in kept:
                kept.add(record.id)
        conn.executemany(
            "DELETE FROM print_queue WHERE id = ?",
            [(row_id,) for row_id in existing if row_id not in kept],
        )

        now = _now()
        updated: set[int] = set()
        for position, (record, values) in enumerate(rows):
            if record.id in kept and record.id not in updated:
                updated.add(record.id)
                changed = existing[record.id] != values
                conn.execute(
                    f"UPDATE print_queue SET position = ?, "
                    f"{', '.join(f'{c} = ?' for c in _DATA_COLUMNS)}, "
                    "updated_at = CASE WHEN ? THEN ? ELSE updated_at END WHERE id = ?",
                    (position, *values, changed, now, record.id),
                )
            else:
                _insert(conn, position, values, record.source or source, now)
    logger.info(f"Print queue replaced: {len(rows)} records")


def append_to_queue(
    records: Sequence[LabelRecord],
    source: str = SOURCE_MANUAL,
    meta: dict[str, str] | None = None,
) -> None:
    """Append *records* as new rows after the current queue.

    Records keep their own source, or get *source* if they have none. *meta*
    key/value pairs are written in the same transaction (e.g. a migration
    marker that must only exist together with the migrated rows).

    Raises:
        ValueError: if a record has an empty title (nothing is written).
    """
    rows = [(record, _values(record)) for record in records]
    with _transaction() as conn:
        start = conn.execute(
            "SELECT COALESCE(MAX(position), -1) + 1 FROM print_queue"
        ).fetchone()[0]
        now = _now()
        for offset, (record, values) in enumerate(rows):
            _insert(conn, start + offset, values, record.source or source, now)
        for key, value in (meta or {}).items():
            conn.execute(
                "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", (key, value)
            )
    logger.info(f"Print queue: {len(rows)} records appended")


def get_meta(key: str) -> str | None:
    """Value of *key* in the meta table, or None."""
    with _transaction() as conn:
        row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row[0] if row else None

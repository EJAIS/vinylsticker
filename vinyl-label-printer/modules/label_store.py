"""
Print queue storage in labels.db (SQLite) — the only code that talks to labels.db.

Every public function opens a short-lived connection, runs in exactly one
transaction (BEGIN IMMEDIATE … COMMIT, ROLLBACK on any error) and closes the
connection again. Foreign keys are enforced on every connection. The app is
single-user; the default rollback journal is used (no WAL), so labels.db is a
plain single file that can be backed up by copying.

Schema versions
---------------
PRAGMA user_version holds the number of applied entries of _MIGRATIONS. Each
connection applies the missing ones in order, inside its transaction. New
versions append an entry and never change an existing one; they must keep the
print_queue table readable for older app versions (add tables / columns only).

Version 1 (app 1.1)
  print_queue  one row per label, ordered by the explicit position column
  meta         key/value pairs written together with queue rows

Version 2 (app 1.2)
  records      the local collection: shared print data, a title per side and
               when each side was last printed (printed_*_at, NULL = never)
  print_queue  + record_id / record_side: the collection record side a row
               was made from; NULL for Discogs rows, one-off entries and rows
               from 1.1. Deleting a record keeps its queue rows (SET NULL).

printed_*_at hold an ISO timestamp (UTC) when the app marks a side as
printed, or an ISO date (YYYY-MM-DD) taken over from a collection CSV import;
modules.records.printed_date() reads both. Marking a side as printed does not
change updated_at (that tracks the print data).

A labels.db written by a 1.1 pre-release may hold a meta key and a source
value of a since removed one-time import; both are kept and simply ignored.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import datetime, timezone

from modules import paths
from modules.logger import get_logger
from modules.records import (
    SIDES,
    CollectionRecord,
    LabelRecord,
    duplicate_key,
    normalise_side,
    printed_date,
    row_from_record,
)

logger = get_logger()

# Values of print_queue.source
SOURCE_MANUAL = "manual"
SOURCE_CSV = "csv"
SOURCE_DISCOGS = "discogs"
SOURCE_COLLECTION = "collection"

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
    # 2 — local collection + link from queue rows to a record side
    (
        """
        CREATE TABLE records (
            id           INTEGER PRIMARY KEY,
            artist       TEXT NOT NULL DEFAULT '',
            label        TEXT NOT NULL DEFAULT '',
            country      TEXT NOT NULL DEFAULT '',
            year         TEXT NOT NULL DEFAULT '',
            catno        TEXT NOT NULL DEFAULT '',
            title_a      TEXT NOT NULL DEFAULT '',
            title_b      TEXT NOT NULL DEFAULT '',
            printed_a_at TEXT,
            printed_b_at TEXT,
            created_at   TEXT NOT NULL,
            updated_at   TEXT NOT NULL,
            CHECK (title_a <> '' OR title_b <> '')
        )
        """,
        "CREATE INDEX records_artist ON records (artist COLLATE NOCASE)",
        "CREATE INDEX records_title_a ON records (title_a COLLATE NOCASE)",
        "CREATE INDEX records_title_b ON records (title_b COLLATE NOCASE)",
        """
        ALTER TABLE print_queue ADD COLUMN record_id INTEGER
            REFERENCES records (id) ON DELETE SET NULL
        """,
        """
        ALTER TABLE print_queue ADD COLUMN record_side TEXT
            CHECK (record_side IN ('A', 'B'))
        """,
        "CREATE INDEX print_queue_record ON print_queue (record_id)",
    ),
)

SCHEMA_VERSION = len(_MIGRATIONS)

_DATA_COLUMNS = ("title", "artist", "label", "country", "year", "side", "catno")
_LINK_COLUMNS = ("record_id", "record_side")
_ROW_COLUMNS = _DATA_COLUMNS + _LINK_COLUMNS
_SELECT_COLUMNS = ", ".join(("id",) + _ROW_COLUMNS + ("source",))

_RECORD_DATA_COLUMNS = ("artist", "label", "country", "year", "catno", "title_a", "title_b")
_RECORD_COLUMNS = (
    ("id",) + _RECORD_DATA_COLUMNS
    + ("printed_a_at", "printed_b_at", "created_at", "updated_at")
)
# Columns the collection search looks in
_RECORD_SEARCH_COLUMNS = _RECORD_DATA_COLUMNS
_PRINTED_COLUMNS = {"A": "printed_a_at", "B": "printed_b_at"}

_warned_newer_schema = False


# ── Connection handling ───────────────────────────────────────────────────────

@contextmanager
def _transaction() -> Iterator[sqlite3.Connection]:
    """Open labels.db, bring the schema up to date, yield inside one transaction."""
    # isolation_level=None: no implicit transactions, BEGIN/COMMIT are explicit
    conn = sqlite3.connect(str(paths.get_labels_db_file()), timeout=10, isolation_level=None)
    try:
        # Per connection, and only outside a transaction (a no-op inside one)
        conn.execute("PRAGMA foreign_keys = ON")
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


def _values(record: LabelRecord, record_id: int | None = None) -> tuple:
    """The row column values of *record* (_ROW_COLUMNS), side normalised to "A" / "B".

    *record_id* overrides record.record_id (a record created in the same
    transaction). A link without a valid side is stored as no link.

    Raises:
        ValueError: if the title is empty.
    """
    if not (record.title or "").strip():
        raise ValueError("A print queue entry needs a title")
    link_id = record_id if record_id is not None else record.record_id
    link_side = record.record_side if record.record_side in SIDES else None
    if link_id is None or link_side is None:
        link_id = link_side = None
    return (
        record.title,
        record.artist or "",
        record.label or "",
        record.country or "",
        record.year or "",
        normalise_side(record.side),
        record.catno or "",
        link_id,
        link_side,
    )


def _insert(
    conn: sqlite3.Connection,
    position: int,
    values: tuple,
    source: str,
    now: str,
) -> None:
    placeholders = ", ".join("?" * (len(_ROW_COLUMNS) + 4))
    conn.execute(
        f"INSERT INTO print_queue (position, {', '.join(_ROW_COLUMNS)}, "
        f"source, created_at, updated_at) VALUES ({placeholders})",
        (position, *values, source, now, now),
    )


def _record_values(record: CollectionRecord) -> tuple[str, ...]:
    """The data column values of *record* (_RECORD_DATA_COLUMNS), stripped.

    Raises:
        ValueError: if both titles are empty.
    """
    values = tuple(
        (getattr(record, column) or "").strip() for column in _RECORD_DATA_COLUMNS
    )
    if not values[-2] and not values[-1]:
        raise ValueError("A collection record needs a title for side A or B")
    return values


def _insert_record(
    conn: sqlite3.Connection,
    values: tuple[str, ...],
    now: str,
    printed: tuple[str | None, str | None] = (None, None),
) -> int:
    cursor = conn.execute(
        f"INSERT INTO records ({', '.join(_RECORD_DATA_COLUMNS)}, printed_a_at, "
        "printed_b_at, created_at, updated_at) "
        f"VALUES ({', '.join('?' * (len(_RECORD_DATA_COLUMNS) + 4))})",
        (*values, *printed, now, now),
    )
    return int(cursor.lastrowid)


def _update_record_data(
    conn: sqlite3.Connection, record_id: int, values: tuple[str, ...], now: str
) -> bool:
    """Write the data columns of record *record_id* if they differ; True if written."""
    differs = " OR ".join(f"{c} IS NOT ?" for c in _RECORD_DATA_COLUMNS)
    cursor = conn.execute(
        f"UPDATE records SET {', '.join(f'{c} = ?' for c in _RECORD_DATA_COLUMNS)}, "
        f"updated_at = ? WHERE id = ? AND ({differs})",
        (*values, now, record_id, *values),
    )
    return cursor.rowcount > 0


def _row_to_record(row: Sequence) -> CollectionRecord:
    data = dict(zip(_RECORD_COLUMNS, row))
    return CollectionRecord(**data)


def _all_records(conn: sqlite3.Connection) -> list[CollectionRecord]:
    """Every collection record, oldest first."""
    rows = conn.execute(f"SELECT {', '.join(_RECORD_COLUMNS)} FROM records ORDER BY id")
    return [_row_to_record(row) for row in rows]


def _row_to_label(row: Sequence) -> LabelRecord:
    """A LabelRecord from a print_queue row selected with _SELECT_COLUMNS."""
    return LabelRecord(
        title=row[1], artist=row[2], label=row[3], country=row[4],
        year=row[5], side=row[6], catno=row[7], record_id=row[8],
        # A side without a record is no link (e.g. the record was deleted)
        record_side=row[9] if row[8] is not None else None,
        id=row[0], source=row[10],
    )


def _prepare_rows(
    records: Sequence[LabelRecord],
    new_records: Sequence[CollectionRecord],
) -> tuple[list[CollectionRecord], list[tuple[str, ...]]]:
    """Validate the collection records to create with a queue write.

    Returns the distinct records to create (*new_records* plus every
    pending_record of *records*, by identity, in this order) and their values.

    Raises:
        ValueError: if a record has no title.
    """
    pending: list[CollectionRecord] = []
    seen: set[int] = set()
    for record in [*new_records, *(r.pending_record for r in records)]:
        if record is not None and id(record) not in seen:
            seen.add(id(record))
            pending.append(record)
    return pending, [_record_values(record) for record in pending]


def _create_pending(
    conn: sqlite3.Connection,
    pending: list[CollectionRecord],
    values: list[tuple[str, ...]],
    now: str,
) -> dict[int, int]:
    """Insert the *pending* records; return {id(record object): new row id}."""
    return {
        id(record): _insert_record(conn, record_values, now)
        for record, record_values in zip(pending, values)
    }


def _row_values(records: Sequence[LabelRecord], created: dict[int, int]) -> list[tuple]:
    return [
        _values(
            record,
            created.get(id(record.pending_record)) if record.pending_record else None,
        )
        for record in records
    ]


# ── Public API ────────────────────────────────────────────────────────────────

def load_queue() -> list[LabelRecord]:
    """Return the print queue in its stored order (with id and source)."""
    with _transaction() as conn:
        rows = conn.execute(
            f"SELECT {_SELECT_COLUMNS} FROM print_queue ORDER BY position, id"
        ).fetchall()
    records = [_row_to_label(row) for row in rows]
    logger.info(f"Print queue loaded: {len(records)} records")
    return records


def queue_count() -> int:
    """Number of entries in the print queue."""
    with _transaction() as conn:
        return conn.execute("SELECT COUNT(*) FROM print_queue").fetchone()[0]


def replace_queue(
    records: Sequence[LabelRecord],
    source: str = SOURCE_MANUAL,
    new_records: Sequence[CollectionRecord] = (),
    record_updates: Sequence[CollectionRecord] = (),
) -> None:
    """Make *records* the whole print queue, in this order.

    A record whose id is in the queue keeps that row (id, source, created_at;
    updated_at changes only if its data changed). Records without a known id
    are new rows with their own source, or *source* if they have none. Queue
    rows that are not in *records* are deleted.

    *new_records* and the pending_record of each queue record are created as
    collection records in the same transaction; queue records with a
    pending_record are linked to its new id.

    *record_updates*: existing collection records whose data fields are
    written (by id) in the same transaction — the queue editor's "Update
    collection". printed_* stay as stored; records that no longer exist are
    skipped. Every row of *records* linked to an updated record is written
    with that record's shared fields and the title of its side
    (records.row_from_record), so the A and B rows of a record agree with it
    afterwards even if only one of them was edited.

    Raises:
        ValueError: if a record has an empty title (nothing is written).
    """
    pending, pending_values = _prepare_rows(records, new_records)
    updates = [(record.id, _record_values(record)) for record in record_updates]
    for record in records:
        _values(record)          # validate before anything is written
    with _transaction() as conn:
        now = _now()
        n_updated = sum(
            _update_record_data(conn, record_id, values, now) for record_id, values in updates
        )
        if updates:
            records = _rows_with_updated_records(conn, records, [rid for rid, _ in updates])
        created = _create_pending(conn, pending, pending_values, now)
        rows = list(zip(records, _row_values(records, created)))
        existing = {
            row[0]: tuple(row[1:])
            for row in conn.execute(f"SELECT id, {', '.join(_ROW_COLUMNS)} FROM print_queue")
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

        updated: set[int] = set()
        for position, (record, values) in enumerate(rows):
            if record.id in kept and record.id not in updated:
                updated.add(record.id)
                changed = existing[record.id] != values
                conn.execute(
                    f"UPDATE print_queue SET position = ?, "
                    f"{', '.join(f'{c} = ?' for c in _ROW_COLUMNS)}, "
                    "updated_at = CASE WHEN ? THEN ? ELSE updated_at END WHERE id = ?",
                    (position, *values, changed, now, record.id),
                )
            else:
                _insert(conn, position, values, record.source or source, now)
    logger.info(
        f"Print queue replaced: {len(rows)} records"
        + (f", {len(pending)} collection records created" if pending else "")
        + (f", {n_updated} collection records updated" if updates else "")
    )


def _rows_with_updated_records(
    conn: sqlite3.Connection,
    records: Sequence[LabelRecord],
    record_ids: Sequence[int | None],
) -> list[LabelRecord]:
    """*records* with every row linked to one of *record_ids* taken from its stored record."""
    wanted = {record_id for record_id in record_ids if record_id is not None}
    if not wanted:
        return list(records)
    placeholders = ", ".join("?" * len(wanted))
    stored = {
        record.id: record
        for record in map(
            _row_to_record,
            conn.execute(
                f"SELECT {', '.join(_RECORD_COLUMNS)} FROM records WHERE id IN ({placeholders})",
                tuple(wanted),
            ),
        )
    }
    return [
        row_from_record(row, stored[row.record_id])
        if row.record_id in stored and row.record_side in SIDES else row
        for row in records
    ]


def append_to_queue(
    records: Sequence[LabelRecord],
    source: str = SOURCE_MANUAL,
    meta: dict[str, str] | None = None,
    new_records: Sequence[CollectionRecord] = (),
) -> None:
    """Append *records* as new rows after the current queue.

    Records keep their own source, or get *source* if they have none. *meta*
    key/value pairs are written in the same transaction (e.g. a marker that
    must only exist together with the rows). *new_records* and pending
    records: as in replace_queue().

    Raises:
        ValueError: if a record has an empty title (nothing is written).
    """
    pending, pending_values = _prepare_rows(records, new_records)
    for record in records:
        _values(record)          # validate before anything is written
    with _transaction() as conn:
        now = _now()
        created = _create_pending(conn, pending, pending_values, now)
        rows = list(zip(records, _row_values(records, created)))
        start = conn.execute(
            "SELECT COALESCE(MAX(position), -1) + 1 FROM print_queue"
        ).fetchone()[0]
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


# ── Collection (records) ──────────────────────────────────────────────────────

def _fold(value: object) -> str:
    return str(value or "").casefold()


def list_records(search: str = "") -> list[CollectionRecord]:
    """The collection, sorted by artist and titles (case-insensitive).

    *search*: only records that contain every whitespace-separated word of it
    in any text column (artist, label, country, year, catalog number, titles),
    case-insensitive also for umlauts (Python casefold, not SQLite's ASCII-only
    LIKE).
    """
    words = [_fold(word) for word in search.split()]
    # All search columns in one text; words contain no whitespace, so a match
    # never spans two columns
    haystack = " || char(10) || ".join(_RECORD_SEARCH_COLUMNS)
    where = ""
    if words:
        where = "WHERE " + " AND ".join(
            f"instr(vlp_fold({haystack}), ?) > 0" for _ in words
        )
    with _transaction() as conn:
        conn.create_function("vlp_fold", 1, _fold, deterministic=True)
        rows = conn.execute(
            f"SELECT {', '.join(_RECORD_COLUMNS)} FROM records {where} "
            "ORDER BY artist COLLATE NOCASE, title_a COLLATE NOCASE, "
            "title_b COLLATE NOCASE, id",
            words,
        ).fetchall()
    return [_row_to_record(row) for row in rows]


def record_count() -> int:
    """Number of records in the collection."""
    with _transaction() as conn:
        return conn.execute("SELECT COUNT(*) FROM records").fetchone()[0]


def _is_printed(value: object) -> int:
    return int(printed_date(value) is not None)


def collection_counts() -> tuple[int, int]:
    """(records, records not printed) of the collection, in one query.

    A record counts as not printed if at least one side with a title has no
    printed date (the same rule as CollectionRecord.unprinted_sides()).
    """
    with _transaction() as conn:
        conn.create_function("vlp_printed", 1, _is_printed, deterministic=True)
        total, unprinted = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM("
            "(COALESCE(title_a, '') <> '' AND NOT vlp_printed(printed_a_at)) "
            "OR (COALESCE(title_b, '') <> '' AND NOT vlp_printed(printed_b_at))"
            "), 0) FROM records"
        ).fetchone()
    return total, unprinted


def get_record(record_id: int) -> CollectionRecord | None:
    """The collection record *record_id*, or None."""
    with _transaction() as conn:
        row = conn.execute(
            f"SELECT {', '.join(_RECORD_COLUMNS)} FROM records WHERE id = ?", (record_id,)
        ).fetchone()
    return _row_to_record(row) if row else None


def add_record(record: CollectionRecord) -> int:
    """Add *record* to the collection (its id is ignored); return the new id.

    Raises:
        ValueError: if both titles are empty.
    """
    values = _record_values(record)
    with _transaction() as conn:
        record_id = _insert_record(conn, values, _now())
    logger.info(f"Collection record {record_id} added")
    return record_id


def update_record(record: CollectionRecord, sync_queue: bool = False) -> int:
    """Write the data fields of *record* (by its id); printed_* stay as stored.

    *sync_queue*: also give the queue rows linked to the record the title of
    their side and the shared fields, in the same transaction (see
    queue_rows_to_sync()). Returns the number of queue rows changed.

    Raises:
        ValueError: if both titles are empty.
        KeyError: if no record has this id.
    """
    values = _record_values(record)
    synced = 0
    with _transaction() as conn:
        now = _now()
        cursor = conn.execute(
            f"UPDATE records SET {', '.join(f'{c} = ?' for c in _RECORD_DATA_COLUMNS)}, "
            "updated_at = ? WHERE id = ?",
            (*values, now, record.id),
        )
        if cursor.rowcount == 0:
            raise KeyError(f"No collection record with id {record.id}")
        if sync_queue:
            stored = replace(record, **dict(zip(_RECORD_DATA_COLUMNS, values)))
            for row in _rows_to_sync(conn, stored):
                conn.execute(
                    f"UPDATE print_queue SET {', '.join(f'{c} = ?' for c in _ROW_COLUMNS)}, "
                    "updated_at = ? WHERE id = ?",
                    (*_values(row), now, row.id),
                )
                synced += 1
    logger.info(
        f"Collection record {record.id} updated"
        + (f", {synced} queue rows synchronised" if sync_queue else "")
    )
    return synced


def _rows_to_sync(conn: sqlite3.Connection, record: CollectionRecord) -> list[LabelRecord]:
    rows = conn.execute(
        f"SELECT {_SELECT_COLUMNS} FROM print_queue WHERE record_id = ? ORDER BY position, id",
        (record.id,),
    ).fetchall()
    result = []
    for row in map(_row_to_label, rows):
        synced = row_from_record(row, record)
        if _values(synced) != _values(row):
            result.append(synced)
    return result


def queue_rows_to_sync(record: CollectionRecord) -> list[LabelRecord]:
    """The queue rows linked to *record* that differ from it, as they would become.

    Each gets the title of its record side (kept if that side has no title)
    and the shared fields of *record*; the data of *record* is used as given
    (e.g. the not yet saved result of the record form).
    """
    values = _record_values(record)
    stored = replace(record, **dict(zip(_RECORD_DATA_COLUMNS, values)))
    with _transaction() as conn:
        return _rows_to_sync(conn, stored)


def delete_records(record_ids: Sequence[int]) -> None:
    """Delete the collection records *record_ids*.

    Their queue rows stay in the print queue and only lose the link
    (ON DELETE SET NULL).
    """
    params = [(record_id,) for record_id in record_ids]
    with _transaction() as conn:
        # ON DELETE SET NULL clears record_id; the side goes with it
        conn.executemany(
            "UPDATE print_queue SET record_side = NULL WHERE record_id = ?", params
        )
        conn.executemany("DELETE FROM records WHERE id = ?", params)
    logger.info(f"Collection: {len(record_ids)} records deleted")


def delete_record(record_id: int) -> None:
    """Delete one collection record; see delete_records()."""
    delete_records([record_id])


# ── Printed marks ─────────────────────────────────────────────────────────────

def mark_sides_printed(sides: Iterable[tuple[int, str]]) -> int:
    """Set printed_<side>_at = now for each (record id, side "A" / "B").

    Returns the number of record sides marked (unknown record ids and invalid
    sides are skipped).
    """
    by_side: dict[str, set[int]] = {side: set() for side in SIDES}
    for record_id, side in sides:
        if record_id is not None and side in SIDES:
            by_side[side].add(record_id)
    marked = 0
    with _transaction() as conn:
        now = _now()
        for side, record_ids in by_side.items():
            column = _PRINTED_COLUMNS[side]
            for record_id in sorted(record_ids):
                cursor = conn.execute(
                    f"UPDATE records SET {column} = ? WHERE id = ?", (now, record_id)
                )
                marked += cursor.rowcount
    logger.info(f"Collection: {marked} record sides marked as printed")
    return marked


def mark_records_printed(record_ids: Sequence[int]) -> None:
    """Mark every side with a title of the records *record_ids* as printed now."""
    with _transaction() as conn:
        now = _now()
        conn.executemany(
            "UPDATE records SET "
            "printed_a_at = CASE WHEN title_a <> '' THEN ? ELSE printed_a_at END, "
            "printed_b_at = CASE WHEN title_b <> '' THEN ? ELSE printed_b_at END "
            "WHERE id = ?",
            [(now, now, record_id) for record_id in record_ids],
        )
    logger.info(f"Collection: {len(record_ids)} records marked as printed")


def clear_printed(record_ids: Sequence[int]) -> None:
    """Mark both sides of the records *record_ids* as not printed."""
    with _transaction() as conn:
        conn.executemany(
            "UPDATE records SET printed_a_at = NULL, printed_b_at = NULL WHERE id = ?",
            [(record_id,) for record_id in record_ids],
        )
    logger.info(f"Collection: {len(record_ids)} records marked as not printed")


# ── Collection import (CSV) ───────────────────────────────────────────────────

@dataclass
class RecordImportResult:
    imported:  int = 0      # new records
    updated:   int = 0      # duplicates whose record was changed ("Update existing")
    unchanged: int = 0      # duplicates whose record already had these values
    skipped:   int = 0      # duplicates left alone ("Skip")


def record_ids_by_key() -> dict[tuple[str, ...], int]:
    """{duplicate key: record id} over the collection; the oldest record wins."""
    with _transaction() as conn:
        records = _all_records(conn)
    result: dict[tuple[str, ...], int] = {}
    for record in records:
        result.setdefault(duplicate_key(record), record.id)
    return result


def count_duplicates(records: Sequence[CollectionRecord]) -> int:
    """How many of *records* duplicate a collection record or an earlier one of *records*."""
    keys = set(record_ids_by_key())
    count = 0
    for record in records:
        key = duplicate_key(record)
        if key in keys:
            count += 1
        keys.add(key)
    return count


def _imported_onto(
    existing: CollectionRecord, record: CollectionRecord, data: dict[str, str]
) -> CollectionRecord:
    """*existing* updated by the imported *record* (*data*: its stripped data columns)."""
    target = replace(existing, **data)
    for side, column in _PRINTED_COLUMNS.items():
        value = record.printed_at(side)
        if value and printed_date(value) != printed_date(existing.printed_at(side)):
            setattr(target, column, value)
    return target


def _same_printed(first: CollectionRecord, second: CollectionRecord) -> bool:
    return (first.printed_a_at, first.printed_b_at) == (second.printed_a_at, second.printed_b_at)


def import_records(
    records: Sequence[CollectionRecord], update_existing: bool
) -> RecordImportResult:
    """Add *records* to the collection in one transaction (a CSV import).

    A record that duplicates a collection record or an earlier record of
    *records* (records.duplicate_key) is skipped, or with *update_existing*
    written onto that record: shared fields and both titles as given,
    printed_*_at only where the import has a value for a different day.
    Records whose values do not change are not written (updated_at stays).
    New records take their printed_*_at from the import.

    If several records share the duplicate key, one that already has the
    imported values counts as unchanged; otherwise the oldest is updated. So
    re-importing an export changes nothing, even if the collection holds
    duplicates of its own.

    Raises:
        ValueError: if a record has no title (nothing is written).
    """
    values = [_record_values(record) for record in records]
    result = RecordImportResult()
    with _transaction() as conn:
        now = _now()
        # Per duplicate key the matching records, oldest first
        by_key: dict[tuple[str, ...], list[CollectionRecord]] = {}
        for existing in _all_records(conn):
            by_key.setdefault(duplicate_key(existing), []).append(existing)
        for record, record_values in zip(records, values):
            key = duplicate_key(record)
            matches = by_key.get(key)
            data = dict(zip(_RECORD_DATA_COLUMNS, record_values))
            if not matches:
                printed = (record.printed_a_at or None, record.printed_b_at or None)
                record_id = _insert_record(conn, record_values, now, printed)
                by_key[key] = [replace(
                    record, id=record_id, printed_a_at=printed[0], printed_b_at=printed[1],
                    **data,
                )]
                result.imported += 1
                continue
            if not update_existing:
                result.skipped += 1
                continue
            targets = [_imported_onto(existing, record, data) for existing in matches]
            if any(
                target == existing and _same_printed(target, existing)
                for target, existing in zip(targets, matches)
            ):
                result.unchanged += 1
                continue
            existing, target = matches[0], targets[0]
            if _update_record_data(conn, existing.id, record_values, now):
                target.updated_at = now
            conn.execute(
                "UPDATE records SET printed_a_at = ?, printed_b_at = ? WHERE id = ?",
                (target.printed_a_at, target.printed_b_at, existing.id),
            )
            matches[0] = target
            result.updated += 1
    logger.info(
        f"Collection import: {result.imported} imported, {result.updated} updated, "
        f"{result.unchanged} unchanged, {result.skipped} skipped"
    )
    return result

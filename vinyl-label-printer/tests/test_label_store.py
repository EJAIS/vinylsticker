"""labels.db: schema, order, side CHECK, transactions and schema versions."""

from __future__ import annotations

import sqlite3

import pytest

from modules import label_store, paths
from modules.records import LabelRecord


def _rec(title: str, side: str = "A", **kwargs) -> LabelRecord:
    fields = dict(artist="Artist", label="Label", country="DE", year="1970", catno="X 1")
    fields.update(kwargs)
    return LabelRecord(title=title, side=side, **fields)


def _connect() -> sqlite3.Connection:
    return sqlite3.connect(str(paths.get_labels_db_file()))


def test_schema_is_created_on_first_use(data_dir):
    assert not (data_dir / "labels.db").exists()
    assert label_store.load_queue() == []
    assert (data_dir / "labels.db").is_file()

    with _connect() as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == label_store.SCHEMA_VERSION
        tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )}
        columns = [row[1] for row in conn.execute("PRAGMA table_info(print_queue)")]
        # Default rollback journal: labels.db stays a plain single file
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "delete"
    assert {"print_queue", "meta", "records"} <= tables
    assert columns == [
        "id", "position", "title", "artist", "label", "country", "year", "side",
        "catno", "source", "created_at", "updated_at", "record_id", "record_side",
    ]
    assert not (data_dir / "labels.db-wal").exists()


def test_replace_append_load_keep_order():
    label_store.replace_queue([_rec("one"), _rec("two", "B"), _rec("three")])
    label_store.append_to_queue([_rec("four"), _rec("five", "B")], source="csv")

    queue = label_store.load_queue()
    assert [r.title for r in queue] == ["one", "two", "three", "four", "five"]
    assert [r.side for r in queue] == ["A", "B", "A", "A", "B"]
    assert [r.source for r in queue] == ["manual"] * 3 + ["csv"] * 2
    assert label_store.queue_count() == 5

    # Replace with a new order: positions follow the list
    label_store.replace_queue(list(reversed(queue)))
    assert [r.title for r in label_store.load_queue()] == [
        "five", "four", "three", "two", "one",
    ]

    label_store.replace_queue([])
    assert label_store.load_queue() == []
    assert label_store.queue_count() == 0


def test_replace_keeps_rows_by_id():
    label_store.replace_queue([_rec("keep"), _rec("drop"), _rec("edit")], source="discogs")
    keep, drop, edit = label_store.load_queue()
    with _connect() as conn:
        before = dict(conn.execute("SELECT id, created_at FROM print_queue"))

    edit.title = "edited"
    copy = LabelRecord(**{**edit.__dict__})          # duplicated row, same id
    new = _rec("new")
    label_store.replace_queue([edit, keep, copy, new])

    queue = label_store.load_queue()
    assert [r.title for r in queue] == ["edited", "keep", "edited", "new"]
    assert queue[0].id == edit.id and queue[1].id == keep.id
    assert queue[2].id not in (edit.id, keep.id, drop.id)
    assert drop.id not in {r.id for r in queue}
    # Kept rows keep their source and creation time
    assert queue[0].source == queue[1].source == "discogs"
    assert queue[2].source == "discogs"      # the copy keeps the row's source
    assert queue[3].source == "manual"
    with _connect() as conn:
        after = dict(conn.execute("SELECT id, created_at FROM print_queue"))
    assert after[keep.id] == before[keep.id]


def test_side_check_and_normalisation():
    label_store.replace_queue([_rec("lower", "b"), _rec("text", "Seite B"), _rec("empty", "")])
    assert [r.side for r in label_store.load_queue()] == ["B", "B", "A"]

    with _connect() as conn, pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO print_queue (position, title, side, created_at, updated_at) "
            "VALUES (9, 'x', 'C', '', '')"
        )
    with _connect() as conn, pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO print_queue (position, title, side, created_at, updated_at) "
            "VALUES (9, '', 'A', '', '')"
        )


def test_empty_title_writes_nothing():
    label_store.replace_queue([_rec("one")])
    with pytest.raises(ValueError):
        label_store.replace_queue([_rec("two"), _rec("  ")])
    with pytest.raises(ValueError):
        label_store.append_to_queue([_rec("two"), _rec("")])
    assert [r.title for r in label_store.load_queue()] == ["one"]


def test_failure_rolls_back(monkeypatch):
    label_store.replace_queue([_rec("one")])
    calls = {"n": 0}
    real_insert = label_store._insert

    def failing_insert(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 2:
            raise sqlite3.OperationalError("disk I/O error")
        real_insert(*args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(label_store, "_insert", failing_insert)
        with pytest.raises(sqlite3.OperationalError):
            label_store.append_to_queue([_rec("two"), _rec("three")], meta={"k": "v"})
        calls["n"] = 0
        with pytest.raises(sqlite3.OperationalError):
            label_store.replace_queue([_rec("a"), _rec("b")])

    assert [r.title for r in label_store.load_queue()] == ["one"]
    assert label_store.get_meta("k") is None


def test_meta_is_written_with_the_rows():
    label_store.append_to_queue([_rec("one")], meta={"marker": "1"})
    assert label_store.get_meta("marker") == "1"
    assert label_store.get_meta("missing") is None


def test_later_schema_version_is_applied_in_order(monkeypatch):
    label_store.replace_queue([_rec("one")])
    next_version = label_store.SCHEMA_VERSION + 1
    extra = ("CREATE TABLE collection_test (id INTEGER PRIMARY KEY)",)
    monkeypatch.setattr(label_store, "_MIGRATIONS", label_store._MIGRATIONS + (extra,))
    monkeypatch.setattr(label_store, "SCHEMA_VERSION", label_store.SCHEMA_VERSION + 1)

    assert [r.title for r in label_store.load_queue()] == ["one"]
    with _connect() as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == next_version
        assert conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE name = 'collection_test'"
        ).fetchone()[0] == 1


def test_newer_schema_version_is_still_readable():
    label_store.replace_queue([_rec("one")])
    with _connect() as conn:
        conn.execute("PRAGMA user_version = 99")
    assert [r.title for r in label_store.load_queue()] == ["one"]
    with _connect() as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 99

"""
The local collection (LOCAL mode): schema version 2, records in labels.db, the
links of queue rows, the collection dialog and "Also save to collection" in
the queue editor ("Add entry" form and CSV import).
"""

from __future__ import annotations

import sqlite3
from dataclasses import asdict

import pytest
from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox

from config import settings
from modules import label_store, paths
from modules.i18n import set_language
from modules.records import (
    CollectionRecord,
    LabelRecord,
    group_rows_into_records,
    queue_rows_for_sides,
    record_from_rows,
)
from ui.collection_dialog import CollectionDialog
from ui.entry_dialog import EntryDialog, EntryInput, entry_records
from ui.review_widget import ReviewDialog
from ui.theme_manager import ThemeManager

# Version 1 schema exactly as written by app 1.1
_V1_SCHEMA = label_store._MIGRATIONS[0]
_SHARED = dict(artist="The Band", label="Label", country="UK", year="1969", catno="R 1")


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance() or QApplication([])
    set_language("EN")
    ThemeManager.instance().set_setting("dark", persist=False)
    yield application


@pytest.fixture(autouse=True)
def settings_file(tmp_path, monkeypatch):
    """A fresh settings.json per test (the remembered checkbox state lives there)."""
    monkeypatch.setattr(settings, "get_settings_file", lambda: tmp_path / "settings.json")


@pytest.fixture(autouse=True)
def delete_windows():
    """Delete the windows a test left open, so later tests never see them."""
    yield
    application = QApplication.instance()
    if application is None:
        return
    for widget in application.topLevelWidgets():
        widget.hide()
        widget.deleteLater()
    application.sendPostedEvents(None, QEvent.Type.DeferredDelete.value)
    application.processEvents()


@pytest.fixture
def message_boxes(monkeypatch):
    """Record static message boxes instead of blocking on them."""
    shown: list[tuple[str, str]] = []
    for name in ("critical", "warning", "information", "question"):
        monkeypatch.setattr(
            QMessageBox, name,
            lambda *args, _name=name, **kwargs: shown.append((_name, args[2])),
        )
    return shown


def _connect() -> sqlite3.Connection:
    return sqlite3.connect(str(paths.get_labels_db_file()))


def _record(**kwargs) -> CollectionRecord:
    fields = dict(_SHARED, title_a="Song A", title_b="Song B")
    fields.update(kwargs)
    return CollectionRecord(**fields)


def _queue_links() -> list[tuple[str, int | None, str | None]]:
    return [(r.title, r.record_id, r.record_side) for r in label_store.load_queue()]


def _write_v1_db() -> None:
    """A populated labels.db as app 1.1 leaves it (schema version 1)."""
    conn = sqlite3.connect(str(paths.get_labels_db_file()))
    try:
        for statement in _V1_SCHEMA:
            conn.execute(statement)
        conn.execute("PRAGMA user_version = 1")
        for position, (title, side, source) in enumerate((
            ("Old A", "A", "manual"), ("Old B", "B", "discogs"), ("Csv", "A", "csv"),
        )):
            conn.execute(
                "INSERT INTO print_queue (position, title, artist, side, catno, source, "
                "created_at, updated_at) VALUES (?, ?, 'Someone', ?, 'X 1', ?, "
                "'2026-01-01T00:00:00+00:00', '2026-01-02T00:00:00+00:00')",
                (position, title, side, source),
            )
        conn.execute("INSERT INTO meta (key, value) VALUES ('k', 'v')")
        conn.commit()
    finally:
        conn.close()


# ── Schema migration 1.1 → 1.2 ────────────────────────────────────────────────

def test_migration_from_a_populated_1_1_database():
    _write_v1_db()
    with _connect() as conn:
        before = conn.execute("SELECT * FROM print_queue ORDER BY id").fetchall()

    queue = label_store.load_queue()

    assert [(r.title, r.side, r.source) for r in queue] == [
        ("Old A", "A", "manual"), ("Old B", "B", "discogs"), ("Csv", "A", "csv"),
    ]
    assert all(r.record_id is None and r.record_side is None for r in queue)
    assert label_store.get_meta("k") == "v"
    assert label_store.list_records() == []
    with _connect() as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 2
        after = conn.execute("SELECT * FROM print_queue ORDER BY id").fetchall()
        record_columns = [row[1] for row in conn.execute("PRAGMA table_info(records)")]
        indexes = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'index'"
        )}
        fks = conn.execute("PRAGMA foreign_key_list(print_queue)").fetchall()
    # Old columns unchanged (incl. timestamps), the two new ones are NULL
    assert [row[:-2] for row in after] == before
    assert all(row[-2:] == (None, None) for row in after)
    assert record_columns == [
        "id", "artist", "label", "country", "year", "catno", "title_a", "title_b",
        "printed_a_at", "printed_b_at", "created_at", "updated_at",
    ]
    assert {"records_artist", "records_title_a", "records_title_b"} <= indexes
    assert [(fk[2], fk[3], fk[4], fk[6]) for fk in fks] == [
        ("records", "record_id", "id", "SET NULL"),
    ]

    # Rows written after the migration keep working, also mixed with old ones
    label_store.append_to_queue([LabelRecord("New", "", "", "", "", "B")])
    assert [r.title for r in label_store.load_queue()] == ["Old A", "Old B", "Csv", "New"]


def test_records_require_a_title_and_link_sides_are_checked():
    label_store.load_queue()                           # creates the schema
    with _connect() as conn, pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO records (artist, created_at, updated_at) VALUES ('x', '', '')"
        )
    with _connect() as conn, pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO print_queue (position, title, side, record_side, created_at, "
            "updated_at) VALUES (0, 't', 'A', 'C', '', '')"
        )
    with pytest.raises(ValueError):
        label_store.add_record(CollectionRecord(artist="x", title_a="  "))


def test_foreign_keys_are_enforced():
    with pytest.raises(sqlite3.IntegrityError):
        label_store.append_to_queue([
            LabelRecord("t", "", "", "", "", "A", record_id=999, record_side="A"),
        ])
    assert label_store.load_queue() == []


# ── Records CRUD and search ───────────────────────────────────────────────────

def test_records_crud():
    record_id = label_store.add_record(_record(title_b=""))
    stored = label_store.get_record(record_id)
    assert stored == _record(title_b="")
    assert stored.id == record_id
    assert stored.printed_a_at is None and stored.printed_b_at is None
    assert stored.created_at and stored.updated_at == stored.created_at

    stored.title_b = " Song B "
    stored.artist = "Other"
    label_store.update_record(stored)
    updated = label_store.get_record(record_id)
    assert (updated.artist, updated.title_a, updated.title_b) == ("Other", "Song A", "Song B")
    assert updated.created_at == stored.created_at

    with pytest.raises(ValueError):
        label_store.update_record(CollectionRecord(id=record_id))
    with pytest.raises(KeyError):
        label_store.update_record(_record(id=12345))

    assert label_store.record_count() == 1
    label_store.delete_record(record_id)
    assert label_store.get_record(record_id) is None
    assert label_store.record_count() == 0


def test_list_records_sorted_and_searched_over_all_text_columns():
    label_store.add_record(_record(artist="beatles", title_a="Help!", title_b="",
                                   label="Parlophone", catno="R 5305", country="UK",
                                   year="1965"))
    label_store.add_record(_record(artist="Animals", title_a="", title_b="Story",
                                   label="Columbia", catno="DB 7301", country="DE",
                                   year="1964"))
    label_store.add_record(_record(artist="Can", title_a="Spoon", title_b="Shikako 100%",
                                   label="United Artists", catno="35 285", year="1971",
                                   country=""))

    def artists(search: str = "") -> list[str]:
        return [r.artist for r in label_store.list_records(search)]

    assert artists() == ["Animals", "beatles", "Can"]      # case-insensitive order
    assert artists("BEATLES") == ["beatles"]
    assert artists("help") == ["beatles"]                  # title A
    assert artists("story") == ["Animals"]                 # title B
    assert artists("columbia") == ["Animals"]              # label
    assert artists("db 7301") == ["Animals"]               # catno, two words
    assert artists("1971") == ["Can"]                      # year
    assert artists("de") == ["Animals"]                    # country
    assert artists("uk 1965") == ["beatles"]               # every word must match
    assert artists("uk 1971") == []
    assert artists("100%") == ["Can"]                      # no wildcards
    assert artists("%") == ["Can"]
    assert artists("_") == []
    assert artists("   ") == artists()

    label_store.add_record(_record(artist="Die Ärzte", title_a="Westerland", title_b=""))
    assert artists("ärzte") == ["Die Ärzte"]               # case-insensitive umlauts
    assert artists("ÄRZTE west") == ["Die Ärzte"]


# ── Links and ON DELETE SET NULL ──────────────────────────────────────────────

def test_queue_rows_carry_their_links_through_load_and_save(app, message_boxes):
    record_id = label_store.add_record(_record())
    record = label_store.get_record(record_id)
    rows = queue_rows_for_sides(record, {"A", "B"})
    label_store.append_to_queue(rows + [LabelRecord("Loose", "", "", "", "", "A")])
    assert _queue_links() == [
        ("Song A", record_id, "A"), ("Song B", record_id, "B"), ("Loose", None, None),
    ]

    # The queue editor keeps the links (also in DISCOGS mode, without the option)
    dlg = ReviewDialog([asdict(r) for r in label_store.load_queue()])
    dlg._table.item(0, 1).setText("Song A edited")
    assert dlg._on_confirm()
    assert _queue_links() == [
        ("Song A edited", record_id, "A"), ("Song B", record_id, "B"), ("Loose", None, None),
    ]


def test_delete_record_keeps_queue_rows_and_drops_the_link():
    keep_id = label_store.add_record(_record(artist="Keep"))
    drop_id = label_store.add_record(_record(artist="Drop"))
    label_store.append_to_queue(
        queue_rows_for_sides(label_store.get_record(drop_id), {"A", "B"})
        + queue_rows_for_sides(label_store.get_record(keep_id), {"B"})
    )
    label_store.delete_record(drop_id)
    assert _queue_links() == [
        ("Song A", None, None), ("Song B", None, None), ("Song B", keep_id, "B"),
    ]
    assert [r.artist for r in label_store.list_records()] == ["Keep"]

    # The foreign key on its own (plain SQL with foreign_keys on): SET NULL
    with _connect() as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("DELETE FROM records WHERE id = ?", (keep_id,))
    assert [title for title, *_ in _queue_links()] == ["Song A", "Song B", "Song B"]
    assert all(rid is None and side is None for _, rid, side in _queue_links())


# ── Building queue rows from checked sides ────────────────────────────────────

def test_queue_rows_for_sides():
    record = _record(id=7, title_b="")
    assert queue_rows_for_sides(record, set()) == []
    assert queue_rows_for_sides(record, {"B"}) == []       # side without a title
    rows = queue_rows_for_sides(_record(id=7), ["B", "A"])
    assert [(r.title, r.side, r.record_id, r.record_side) for r in rows] == [
        ("Song A", "A", 7, "A"), ("Song B", "B", 7, "B"),
    ]
    for row in rows:
        assert (row.artist, row.label, row.country, row.year, row.catno) == (
            "The Band", "Label", "UK", "1969", "R 1",
        )


def test_collection_dialog_add_checked_sides_to_the_queue(app, monkeypatch, message_boxes):
    only_a = label_store.add_record(_record(artist="Alpha", title_b=""))
    both = label_store.add_record(_record(artist="Beta"))
    only_b = label_store.add_record(_record(artist="Gamma", title_a=""))
    label_store.append_to_queue([LabelRecord("Old", "", "", "", "", "A")])

    dlg = CollectionDialog()
    assert dlg._stack.currentIndex() == 0
    assert dlg._table.rowCount() == 3
    assert not dlg._btn_queue.isEnabled()
    # A side without a title cannot be checked
    assert not dlg.set_side_checked(only_a, "B", True)
    assert not dlg.set_side_checked(only_b, "A", True)

    dlg._set_all_checked(True)
    assert dlg.checked_sides() == {only_a: {"A"}, both: {"A", "B"}, only_b: {"B"}}
    dlg._set_all_checked(False)
    assert dlg.checked_sides() == {}
    assert not dlg._btn_queue.isEnabled()

    assert dlg.set_side_checked(only_b, "B", True)
    assert dlg.set_side_checked(both, "B", True)
    assert dlg.set_side_checked(both, "A", True)
    assert dlg._btn_queue.isEnabled()
    assert [(r.artist, r.title, r.side) for r in dlg.build_queue_rows()] == [
        ("Beta", "Song A", "A"), ("Beta", "Song B", "B"), ("Gamma", "Song B", "B"),
    ]

    # Checked sides hidden by the search stay checked and are added too
    dlg._search.setText("gamma")
    assert [dlg._table.isRowHidden(r) for r in range(3)] == [True, True, False]
    assert len(dlg.build_queue_rows()) == 3
    dlg._search.setText("")

    reviewed: list[list[tuple]] = []

    def fake_exec(review):
        reviewed.append([
            (row["title"], row["record_id"], row["record_side"])
            for row in (review._read_row(r) for r in range(review._table.rowCount()))
        ])
        assert review._import_mode
        monkeypatch.setattr(review, "_ask_append_or_replace", lambda n: "append")
        return QDialog.DialogCode.Accepted if review._on_confirm() else 0

    monkeypatch.setattr(ReviewDialog, "exec", fake_exec)
    dlg._on_add_to_queue()
    assert reviewed == [[
        ("Song A", both, "A"), ("Song B", both, "B"), ("Song B", only_b, "B"),
    ]]
    assert dlg.result() == QDialog.DialogCode.Accepted
    assert _queue_links() == [
        ("Old", None, None),
        ("Song A", both, "A"), ("Song B", both, "B"), ("Song B", only_b, "B"),
    ]
    assert {r.source for r in label_store.load_queue()[1:]} == {"collection"}


def test_collection_dialog_review_cancelled_keeps_dialog_open(app, monkeypatch):
    record_id = label_store.add_record(_record())
    dlg = CollectionDialog()
    dlg.set_side_checked(record_id, "A", True)
    monkeypatch.setattr(ReviewDialog, "exec", lambda self: QDialog.DialogCode.Rejected)
    dlg._on_add_to_queue()
    assert dlg.result() == 0
    assert dlg.checked_sides() == {record_id: {"A"}}
    assert label_store.load_queue() == []


def test_collection_dialog_empty_new_edit_delete(app, monkeypatch, message_boxes):
    dlg = CollectionDialog()
    assert dlg._stack.currentIndex() == 1                  # empty hint + "New record"
    assert not dlg._btn_queue.isEnabled()

    entered = iter([_record(title_b=""), None])
    monkeypatch.setattr(dlg, "_edit_record", lambda record: next(entered))
    dlg._on_new()
    dlg._on_new()                                          # cancelled: nothing added
    assert dlg._stack.currentIndex() == 0
    assert [r.title_a for r in label_store.list_records()] == ["Song A"]
    record_id = label_store.list_records()[0].id
    assert dlg._selected_ids() == [record_id]              # the new record is selected

    dlg.set_side_checked(record_id, "A", True)
    edited = label_store.get_record(record_id)
    edited.title_a = ""
    edited.title_b = "Now B"
    monkeypatch.setattr(dlg, "_edit_record", lambda record: edited)
    dlg.edit_record_id(record_id)
    assert label_store.get_record(record_id).title_b == "Now B"
    # Side A lost its title: unchecked and disabled
    assert dlg.checked_sides() == {}
    assert not dlg.set_side_checked(record_id, "A", True)

    label_store.append_to_queue(queue_rows_for_sides(edited, {"B"}))
    monkeypatch.setattr(dlg, "_confirm_delete", lambda ids: False)
    dlg._on_delete()
    assert label_store.record_count() == 1
    monkeypatch.setattr(dlg, "_confirm_delete", lambda ids: True)
    dlg._on_delete()
    assert label_store.record_count() == 0
    assert dlg._stack.currentIndex() == 1
    assert _queue_links() == [("Now B", None, None)]       # queue row stays
    assert message_boxes == []


def test_record_form_edit_mode_uses_the_entry_validation(app):
    base = label_store.get_record(label_store.add_record(_record()))
    dlg = EntryDialog(record_mode=True, record=base)
    assert dlg.windowTitle() == "Edit record"
    assert not dlg._btn_add_next.isVisibleTo(dlg)
    assert not dlg._chk_collection.isVisibleTo(dlg)
    assert dlg.entry() == EntryInput(**_SHARED, title_a="Song A", title_b="Song B")

    dlg.set_entry(EntryInput(**{**_SHARED, "year": "69"}, title_a="x"))
    dlg._on_add()
    assert dlg.result() == 0
    assert dlg._lbl_message.text() == "Year: leave empty or enter four digits (e.g. 1969)."
    dlg.set_entry(EntryInput(**_SHARED))
    dlg._on_add()
    assert dlg.result() == 0

    dlg.set_entry(EntryInput(**_SHARED, title_b="Only B"))
    dlg._on_add()
    assert dlg.result() == QDialog.DialogCode.Accepted
    record = dlg.record()
    assert (record.id, record.title_a, record.title_b) == (base.id, "", "Only B")
    assert record.created_at == base.created_at

    assert EntryDialog(record_mode=True).windowTitle() == "New record"


# ── CSV import grouping ───────────────────────────────────────────────────────

def _row(title: str, side: str, **kwargs) -> LabelRecord:
    fields = dict(_SHARED)
    fields.update(kwargs)
    return LabelRecord(title=title, side=side, **fields)


def test_group_rows_into_records():
    rows = [
        _row("Pair A", "A"), _row("Pair B", "B", artist=" The Band "),   # A+B pair
        _row("Lone A", "A"),                                               # lone A
        _row("Lone B", "B", artist="Other"),                               # lone B
        _row("Diff A", "A"), _row("Diff B", "B", catno="R 2"),             # other catno
        _row("B first", "B"), _row("A after", "A"),                        # wrong order
    ]
    groups = group_rows_into_records(rows)
    assert groups == [[0, 1], [2], [3], [4], [5], [6], [7]]

    records = [record_from_rows([rows[i] for i in group]) for group in groups]
    assert [(r.title_a, r.title_b) for r in records] == [
        ("Pair A", "Pair B"), ("Lone A", ""), ("", "Lone B"),
        ("Diff A", ""), ("", "Diff B"), ("", "B first"), ("A after", ""),
    ]
    assert records[2].artist == "Other" and records[4].catno == "R 2"
    assert group_rows_into_records([]) == []


def test_csv_import_with_collection_creates_linked_records(app, monkeypatch,
                                                         message_boxes, tmp_path):
    csv_file = tmp_path / "in.csv"
    csv_file.write_text(
        "Title;Artist;Label;Country;Year;Side;CatNo\n"
        "Pair A;Band;L;UK;1969;A;R 1\n"
        "Pair B; Band ;L;UK;1969;B;R 1\n"
        "Lone A;Solo;L;UK;1970;A;R 2\n"
        "Lone B;Other;L;UK;1971;B;R 3\n"
        "Diff A;Band;L;UK;1969;A;R 4\n"
        "Diff B;Band;L;UK;1969;B;R 5\n",
        encoding="utf-8",
    )
    settings.set_save_to_collection(True)
    dlg = ReviewDialog([], collection=True)
    assert dlg.csv_to_collection()
    assert dlg.import_csv(csv_file)
    assert message_boxes[-1] == (
        "information",
        "6 entries imported, 0 skipped (no title).\n"
        "On save, 5 record(s) will be created in the collection.",
    )
    assert label_store.record_count() == 0                 # nothing written yet

    assert dlg._on_confirm()
    records = label_store.list_records()
    assert sorted((r.artist, r.catno, r.title_a, r.title_b) for r in records) == [
        ("Band", "R 1", "Pair A", "Pair B"),
        ("Band", "R 4", "Diff A", ""),
        ("Band", "R 5", "", "Diff B"),
        ("Other", "R 3", "", "Lone B"),
        ("Solo", "R 2", "Lone A", ""),
    ]
    by_catno = {r.catno: r.id for r in records}
    assert _queue_links() == [
        ("Pair A", by_catno["R 1"], "A"), ("Pair B", by_catno["R 1"], "B"),
        ("Lone A", by_catno["R 2"], "A"), ("Lone B", by_catno["R 3"], "B"),
        ("Diff A", by_catno["R 4"], "A"), ("Diff B", by_catno["R 5"], "B"),
    ]


def test_csv_import_without_collection_behaves_like_1_1(app, message_boxes, tmp_path):
    csv_file = tmp_path / "in.csv"
    csv_file.write_text("Title;Side\nOne;A\nTwo;B\n", encoding="utf-8")
    settings.set_save_to_collection(False)
    dlg = ReviewDialog([], collection=True)
    assert not dlg._chk_csv_collection.isChecked()
    assert dlg.import_csv(csv_file)
    assert message_boxes[-1] == ("information", "2 entries imported, 0 skipped (no title).")
    assert dlg._on_confirm()
    assert label_store.record_count() == 0
    assert _queue_links() == [("One", None, None), ("Two", None, None)]

    # DISCOGS mode: no checkbox, never a record
    settings.set_save_to_collection(True)
    other = ReviewDialog([])
    assert not other._chk_csv_collection.isVisibleTo(other)
    assert not other.csv_to_collection()


# ── "Add entry" form with "Also save to collection" ───────────────────────────

def test_entry_form_checkbox_is_remembered_and_hidden_in_discogs_mode(app):
    settings.set_save_to_collection(True)
    dlg = EntryDialog(collection_option=True)
    assert dlg._chk_collection.isVisibleTo(dlg)
    assert dlg._chk_collection.isChecked() and dlg.save_to_collection()
    dlg._chk_collection.setChecked(False)
    assert settings.get_save_to_collection() is False
    assert not EntryDialog(collection_option=True).save_to_collection()

    discogs = EntryDialog()                                # DISCOGS mode
    assert not discogs._chk_collection.isVisibleTo(discogs)
    settings.set_save_to_collection(True)
    assert not EntryDialog().save_to_collection()


def test_entry_default_is_save_to_collection():
    assert settings.get_save_to_collection() is True


def test_entry_with_collection_on_creates_a_linked_record(app, message_boxes):
    dlg = ReviewDialog([], collection=True)
    dlg.add_entry_rows(entry_records(EntryInput(**_SHARED, title_a="A1", title_b="B1")), True)
    dlg.add_entry_rows(entry_records(EntryInput(**_SHARED, title_b="Only B")), True)
    # Unchecked rows are not queued, but still belong to their record
    dlg._table.item(2, 0).setCheckState(Qt.CheckState.Unchecked)
    assert label_store.record_count() == 0
    assert dlg._on_confirm()

    records = {r.title_a or r.title_b: r for r in label_store.list_records()}
    assert set(records) == {"A1", "Only B"}
    assert (records["A1"].title_a, records["A1"].title_b) == ("A1", "B1")
    assert (records["A1"].artist, records["A1"].catno) == ("The Band", "R 1")
    assert (records["Only B"].title_a, records["Only B"].title_b) == ("", "Only B")
    assert _queue_links() == [
        ("A1", records["A1"].id, "A"), ("B1", records["A1"].id, "B"),
    ]


def test_entry_with_collection_off_behaves_like_1_1(app, message_boxes):
    dlg = ReviewDialog([], collection=True)
    dlg.add_entry_rows(entry_records(EntryInput(**_SHARED, title_a="A1", title_b="B1")), False)
    assert dlg._on_confirm()
    assert label_store.record_count() == 0
    assert _queue_links() == [("A1", None, None), ("B1", None, None)]


def test_edits_in_the_editor_go_into_the_new_record(app, message_boxes):
    dlg = ReviewDialog([], collection=True)
    dlg.add_entry_rows(entry_records(EntryInput(**_SHARED, title_a="A1", title_b="B1")), True)
    dlg._table.item(0, 1).setText("A1 fixed")
    dlg._delete_rows([1])                                  # removed row: not in the record
    assert dlg._on_confirm()
    [record] = label_store.list_records()
    assert (record.title_a, record.title_b) == ("A1 fixed", "")


def test_cancel_leaves_the_collection_unchanged(app, monkeypatch, message_boxes):
    existing = label_store.add_record(_record(artist="Existing"))
    dlg = ReviewDialog([], collection=True)
    dlg.show()
    dlg.add_entry_rows(entry_records(EntryInput(**_SHARED, title_a="A1")), True)
    monkeypatch.setattr(dlg, "_ask_unsaved", lambda: "discard")
    dlg.reject()
    assert not dlg.isVisible()
    assert [r.id for r in label_store.list_records()] == [existing]
    assert label_store.load_queue() == []


def test_failed_save_writes_neither_queue_nor_records(app, monkeypatch, message_boxes):
    dlg = ReviewDialog([], collection=True)
    dlg.add_entry_rows(entry_records(EntryInput(**_SHARED, title_a="A1")), True)

    def failing_insert(*args, **kwargs):
        raise sqlite3.OperationalError("disk I/O error")

    monkeypatch.setattr(label_store, "_insert", failing_insert)
    assert not dlg._on_confirm()
    assert message_boxes[-1][0] == "critical"
    monkeypatch.undo()
    assert label_store.record_count() == 0
    assert label_store.load_queue() == []


# ── Main window / mode switch ─────────────────────────────────────────────────

def test_discogs_mode_keeps_the_collection_out_of_reach(app, monkeypatch, message_boxes):
    from modules.data_source import DataSourceMode
    from ui.app import MainWindow
    from ui.discogs_dialog import DiscogsDialog

    record_id = label_store.add_record(_record())
    label_store.append_to_queue(queue_rows_for_sides(label_store.get_record(record_id), "A"))
    opened: list[str] = []

    def fake_discogs_init(self, parent=None):
        QDialog.__init__(self, parent)
        opened.append("discogs")

    monkeypatch.setattr(DiscogsDialog, "__init__", fake_discogs_init)
    monkeypatch.setattr(DiscogsDialog, "exec", lambda self: QDialog.DialogCode.Rejected)
    monkeypatch.setattr(
        CollectionDialog, "exec",
        lambda self: opened.append("collection") or QDialog.DialogCode.Rejected,
    )
    editors: list[bool] = []
    monkeypatch.setattr(
        ReviewDialog, "exec",
        lambda self: editors.append(self._collection) or QDialog.DialogCode.Rejected,
    )

    window = MainWindow()
    window.on_mode_changed(DataSourceMode.DISCOGS.value)
    window.on_load_data()
    window.on_open_queue()
    window.on_mode_changed(DataSourceMode.LOCAL.value)
    window.on_load_data()
    window.on_open_queue()

    assert opened == ["discogs", "collection"]
    assert editors == [False, True]
    assert label_store.record_count() == 1
    assert _queue_links() == [("Song A", record_id, "A")]

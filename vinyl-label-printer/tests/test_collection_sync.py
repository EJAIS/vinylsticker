"""
Collection part 2 (LOCAL mode): printed marking, the sync between the print
queue and the collection, and the collection CSV import / export (incl. the
queue editor's CSV import linking to existing records).
"""

from __future__ import annotations

import sqlite3
from dataclasses import asdict, replace
from datetime import date, datetime, timezone

import pytest
from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox

from config import settings
from modules import csv_io, label_store
from modules.csv_io import (
    CsvImportError,
    default_collection_export_name,
    read_collection_csv,
    write_collection_csv,
)
from modules.data_source import DataSourceMode
from modules.i18n import set_language
from modules.records import (
    CollectionRecord,
    LabelRecord,
    duplicate_key,
    printed_date,
    queue_rows_for_sides,
    record_with_rows,
)
from ui.collection_dialog import CollectionDialog, _DateItem
from ui.review_widget import ReviewDialog

_SHARED = dict(artist="The Band", label="Label", country="UK", year="1969", catno="R 1")
_COL_TITLE, _COL_ARTIST, _COL_SIDE = 1, 2, 7       # queue editor columns


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance() or QApplication([])
    set_language("EN")
    yield application


@pytest.fixture(autouse=True)
def settings_file(tmp_path, monkeypatch):
    """A fresh settings.json per test (LOCAL mode is the default)."""
    monkeypatch.setattr(settings, "get_settings_file", lambda: tmp_path / "settings.json")


@pytest.fixture(autouse=True)
def delete_windows():
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


def _record(**kwargs) -> CollectionRecord:
    fields = dict(_SHARED, title_a="Song A", title_b="Song B")
    fields.update(kwargs)
    return CollectionRecord(**fields)


def _add(**kwargs) -> CollectionRecord:
    return label_store.get_record(label_store.add_record(_record(**kwargs)))


def _queue() -> list[tuple]:
    return [
        (r.title, r.artist, r.side, r.record_id, r.record_side)
        for r in label_store.load_queue()
    ]


def _printed(record_id: int) -> tuple[str | None, str | None]:
    record = label_store.get_record(record_id)
    return record.printed_a_at, record.printed_b_at


def _editor(collection: bool = True) -> ReviewDialog:
    return ReviewDialog(
        [asdict(r) for r in label_store.load_queue()], collection=collection
    )


# ── Printed marking: store and records helpers ────────────────────────────────

def test_printed_date_reads_timestamps_and_dates():
    assert printed_date(None) is None and printed_date("") is None
    assert printed_date("nonsense") is None
    assert printed_date("2026-03-04") == date(2026, 3, 4)
    stamp = datetime(2026, 3, 4, 12, 0, tzinfo=timezone.utc)
    assert printed_date(stamp.isoformat()) == stamp.astimezone().date()


def test_mark_sides_printed_only_touches_the_given_sides():
    first = _add()
    second = _add(artist="Other")
    before = label_store.get_record(first.id).updated_at
    assert label_store.mark_sides_printed(
        [(first.id, "B"), (second.id, "A"), (second.id, "A"), (999, "A"), (first.id, "C")]
    ) == 2
    assert _printed(first.id)[0] is None
    assert printed_date(_printed(first.id)[1]) == date.today()
    assert printed_date(_printed(second.id)[0]) == date.today()
    assert _printed(second.id)[1] is None
    # Printed marks are not data edits
    assert label_store.get_record(first.id).updated_at == before


def test_mark_and_clear_records_printed():
    both = _add()
    only_a = _add(artist="Solo", title_b="")
    label_store.mark_records_printed([both.id, only_a.id])
    assert all(printed_date(v) == date.today() for v in _printed(both.id))
    assert printed_date(_printed(only_a.id)[0]) == date.today()
    assert _printed(only_a.id)[1] is None                  # side without a title
    label_store.clear_printed([both.id])
    assert _printed(both.id) == (None, None)
    assert _printed(only_a.id)[0] is not None


def test_unprinted_sides():
    record = _record(title_b="", printed_a_at=None)
    assert record.unprinted_sides() == ["A"]
    record.printed_a_at = "2026-01-01"
    assert record.unprinted_sides() == []
    assert _record(printed_b_at="2026-01-01").unprinted_sides() == ["A"]


# ── Printed marking: the question after "Print" ───────────────────────────────

@pytest.fixture
def window(app, monkeypatch, message_boxes):
    """A main window whose PDF generation and printing do nothing."""
    import ui.app as app_module

    calls = {"pdf_error": None, "print_error": None}

    def fake_generate_pdf(records, output_path, **kwargs):
        if calls["pdf_error"]:
            raise calls["pdf_error"]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"%PDF-1.4\n")
        return output_path

    def fake_print_pdf(path):
        if calls["print_error"]:
            raise calls["print_error"]

    monkeypatch.setattr(app_module, "generate_pdf", fake_generate_pdf)
    monkeypatch.setattr(app_module, "print_pdf", fake_print_pdf)
    monkeypatch.setattr(app_module.PreviewWidget, "load_pdf", lambda self, path: None)
    monkeypatch.setattr(app_module, "get_output_dir", lambda: label_store.paths.get_data_dir())

    win = app_module.MainWindow()
    win.asked = []
    win.answer = True

    def fake_ask(n_labels):
        win.asked.append(n_labels)
        return win.answer

    monkeypatch.setattr(win, "_ask_mark_printed", fake_ask)
    win.calls = calls
    return win


def _queue_record_with_extra_row() -> CollectionRecord:
    record = _add()
    label_store.append_to_queue(
        queue_rows_for_sides(record, "AB") + [LabelRecord("One-off", "X", "", "", "", "A")]
    )
    return record


def test_print_question_is_asked_once_for_linked_rows_only(window):
    record = _queue_record_with_extra_row()
    window._load_queue()

    window.on_create_pdf()                                 # a preview is no print
    assert window.asked == []
    assert _printed(record.id) == (None, None)

    window.on_print()
    assert window.asked == [2]                              # the unlinked row is ignored
    assert all(printed_date(v) == date.today() for v in _printed(record.id))

    # Printing the same queue again: no second question, nor from "Create PDF"
    label_store.clear_printed([record.id])
    window.on_print()
    window.on_create_pdf()
    assert window.asked == [2]
    assert _printed(record.id) == (None, None)

    # A changed queue regenerates the PDF without asking; printing it asks again
    label_store.append_to_queue(queue_rows_for_sides(record, "A"))
    window._load_queue()
    window.on_create_pdf()
    assert window.asked == [2]
    window.on_print()                                      # prints the regenerated PDF
    assert window.asked == [2, 3]
    window.on_print()
    assert window.asked == [2, 3]


def test_create_pdf_answered_no_does_not_use_up_the_question(window):
    """The 1.2 bug: "No" after "Create PDF" (only a preview) blocked the question at Print."""
    record = _queue_record_with_extra_row()
    window._load_queue()
    window.answer = False
    window.on_create_pdf()
    window.answer = True
    window.on_print()
    assert window.asked == [2]
    assert all(printed_date(v) == date.today() for v in _printed(record.id))


def test_print_question_answered_no_marks_nothing(window):
    record = _queue_record_with_extra_row()
    window._load_queue()
    window.answer = False
    window.on_print()                                      # no PDF yet: nothing printed
    assert window.asked == []
    window.on_create_pdf()
    window.on_print()
    assert window.asked == [2]
    assert _printed(record.id) == (None, None)


def test_no_question_when_print_or_pdf_fails(window, message_boxes):
    record = _queue_record_with_extra_row()
    window._load_queue()

    window.calls["pdf_error"] = RuntimeError("disk full")
    window.on_create_pdf()
    assert message_boxes[-1][0] == "critical"
    assert window.asked == []

    window.calls["pdf_error"] = None
    window._create_pdf()                                   # e.g. a new start position
    assert window.asked == []
    window.calls["print_error"] = RuntimeError("xdg-open failed")
    window.on_print()
    assert message_boxes[-1][0] == "critical"
    assert window.asked == []
    assert _printed(record.id) == (None, None)

    window.calls["print_error"] = None
    window.on_print()
    assert window.asked == [2]


def test_no_question_when_the_watermark_is_missing(window, tmp_path):
    _queue_record_with_extra_row()
    window._load_queue()
    window._watermark_path = tmp_path / "gone.png"
    window.on_create_pdf()
    assert window.asked == []


def test_no_question_in_discogs_mode_or_without_linked_rows(window):
    label_store.append_to_queue([LabelRecord("One-off", "X", "", "", "", "A")])
    window._load_queue()
    window.on_create_pdf()
    window.on_print()
    assert window.asked == []

    record = _add()
    label_store.append_to_queue(queue_rows_for_sides(record, "A"))
    window._load_queue()
    window.on_mode_changed(DataSourceMode.DISCOGS.value)
    window.on_create_pdf()
    window.on_print()
    assert window.asked == []
    assert _printed(record.id) == (None, None)


# ── Printed marking in the collection dialog ──────────────────────────────────

def test_collection_dialog_shows_and_sets_printed_dates(app, message_boxes):
    both = _add()
    only_a = _add(artist="Solo", title_b="")
    dlg = CollectionDialog()
    assert dlg._table.horizontalHeaderItem(9).text() == "Printed A"
    assert dlg._table.horizontalHeaderItem(10).text() == "Printed B"
    assert not dlg._btn_mark_printed.isEnabled()

    dlg._reselect([both.id, only_a.id])
    assert sorted(dlg._selected_ids()) == sorted([both.id, only_a.id])
    assert dlg._btn_mark_printed.isEnabled()
    dlg.mark_selected(True)
    assert printed_date(_printed(only_a.id)[0]) == date.today()
    assert _printed(only_a.id)[1] is None
    row = dlg._row_of(only_a.id)
    assert dlg._table.item(row, 9).text() != ""
    assert dlg._table.item(row, 10).text() == ""
    assert sorted(dlg._selected_ids()) == sorted([both.id, only_a.id])   # kept

    dlg._reselect([both.id])
    dlg.mark_selected(False)
    assert _printed(both.id) == (None, None)
    assert dlg._table.item(dlg._row_of(both.id), 9).text() == ""
    assert _printed(only_a.id)[0] is not None
    assert message_boxes == []


def test_printed_columns_sort_by_date():
    early, late, never = _DateItem("2025-12-31"), _DateItem("2026-01-02"), _DateItem(None)
    assert never < early < late
    assert not late < early


def test_only_not_printed_filter_and_select_all_unprinted(app):
    printed = _add(artist="A1", printed_a_at=None)
    half = _add(artist="A2")
    fresh = _add(artist="A3")
    only_a = _add(artist="A4", title_b="")
    label_store.mark_records_printed([printed.id, only_a.id])
    label_store.mark_sides_printed([(half.id, "A")])

    dlg = CollectionDialog()
    assert dlg._btn_all.text() == "Select all sides"
    dlg._chk_unprinted.setChecked(True)
    assert dlg._btn_all.text() == "Select all unprinted sides"
    visible = {
        dlg._record_id(row) for row in range(dlg._table.rowCount())
        if not dlg._table.isRowHidden(row)
    }
    assert visible == {half.id, fresh.id}

    dlg._set_all_checked(True)
    assert dlg.checked_sides() == {half.id: {"B"}, fresh.id: {"A", "B"}}

    # Combined with the search
    dlg._set_all_checked(False)
    dlg._search.setText("A3")
    dlg._set_all_checked(True)
    assert dlg.checked_sides() == {fresh.id: {"A", "B"}}

    dlg._search.setText("")
    dlg._chk_unprinted.setChecked(False)
    assert dlg._btn_all.text() == "Select all sides"
    assert not any(dlg._table.isRowHidden(row) for row in range(dlg._table.rowCount()))
    dlg._set_all_checked(True)
    assert dlg.checked_sides()[printed.id] == {"A", "B"}


# ── Sync: queue editor → collection ───────────────────────────────────────────

def _linked_queue(record: CollectionRecord, extra: bool = False) -> None:
    rows = queue_rows_for_sides(record, "AB")
    if extra:
        rows.append(LabelRecord("One-off", "X", "", "", "", "A"))
    label_store.append_to_queue(rows)


def _answer_sync(monkeypatch, dlg: ReviewDialog, answer: bool) -> list[int]:
    asked: list[int] = []
    monkeypatch.setattr(
        dlg, "_ask_update_collection", lambda n: asked.append(n) or answer
    )
    return asked


def test_queue_edits_update_the_collection_on_request(app, monkeypatch, message_boxes):
    record = _add()
    label_store.mark_sides_printed([(record.id, "A")])
    _linked_queue(record, extra=True)
    dlg = _editor()
    dlg._table.item(0, _COL_TITLE).setText("New A")
    dlg._table.item(1, _COL_ARTIST).setText("New Band")
    dlg._table.item(2, _COL_TITLE).setText("One-off edited")   # unlinked: not counted
    asked = _answer_sync(monkeypatch, dlg, True)
    assert dlg._on_confirm()
    assert asked == [2]
    stored = label_store.get_record(record.id)
    assert (stored.title_a, stored.title_b, stored.artist) == ("New A", "Song B", "New Band")
    assert stored.printed_a_at is not None                     # printed dates stay
    # Both rows of the record follow it, also the A row whose artist was not edited
    assert _queue() == [
        ("New A", "New Band", "A", record.id, "A"),
        ("Song B", "New Band", "B", record.id, "B"),
        ("One-off edited", "X", "A", None, None),
    ]


def test_update_collection_brings_the_other_side_in_step(app, monkeypatch, message_boxes):
    """The 1.2 bug: the unedited A row kept the old artist; the next save reverted the record."""
    record = _add()
    _linked_queue(record)
    dlg = _editor()
    dlg._table.item(1, _COL_ARTIST).setText("New Band")      # only the B row
    asked = _answer_sync(monkeypatch, dlg, True)
    assert dlg._on_confirm()
    assert asked == [1]
    assert label_store.get_record(record.id).artist == "New Band"
    assert [(title, artist) for title, artist, *_ in _queue()] == [
        ("Song A", "New Band"), ("Song B", "New Band"),
    ]

    # Saving again without edits: no question, the record keeps the new artist
    again = _editor()
    asked = _answer_sync(monkeypatch, again, True)
    assert again._on_confirm()
    assert asked == []
    assert label_store.get_record(record.id).artist == "New Band"


def test_record_updates_only_rewrite_rows_of_updated_records():
    edited = _add()
    other = _add(artist="Other Band")
    gone = _add(artist="Deleted later")
    rows = [
        *queue_rows_for_sides(edited, "AB"),
        # Differs from its record on purpose ("Only the print queue" earlier)
        replace(queue_rows_for_sides(other, "A")[0], title="Queue-only title"),
        *queue_rows_for_sides(gone, "A"),
    ]
    label_store.append_to_queue(rows)
    queue = label_store.load_queue()
    queue[2].artist = "Edited in the queue only"
    label_store.delete_records([gone.id])
    label_store.replace_queue(
        queue[:3],
        record_updates=[replace(edited, artist="New Band"), replace(gone, artist="X")],
    )
    assert _queue() == [
        ("Song A", "New Band", "A", edited.id, "A"),
        ("Song B", "New Band", "B", edited.id, "B"),
        ("Queue-only title", "Edited in the queue only", "A", other.id, "A"),
    ]
    assert label_store.get_record(other.id) == other
    assert label_store.get_record(gone.id) is None


def test_only_the_print_queue_leaves_the_collection_unchanged(app, monkeypatch, message_boxes):
    record = _add()
    _linked_queue(record)
    dlg = _editor()
    dlg._table.item(0, _COL_TITLE).setText("New A")
    asked = _answer_sync(monkeypatch, dlg, False)
    assert dlg._on_confirm()
    assert asked == [1]
    assert label_store.get_record(record.id) == record
    assert _queue()[0] == ("New A", "The Band", "A", record.id, "A")

    # The row still differs from its record: the next save asks again (intended)
    again = _editor()
    asked = _answer_sync(monkeypatch, again, False)
    assert again._on_confirm()
    assert asked == [1]


def test_no_sync_question_without_changes_or_in_discogs_mode(app, monkeypatch, message_boxes):
    record = _add()
    _linked_queue(record)
    dlg = _editor()
    asked = _answer_sync(monkeypatch, dlg, True)
    dlg._table.item(0, 0).setCheckState(Qt.CheckState.Unchecked)    # removing is no edit
    assert dlg._on_confirm()
    assert asked == []

    label_store.replace_queue(queue_rows_for_sides(record, "AB"))
    discogs = _editor(collection=False)
    asked = _answer_sync(monkeypatch, discogs, True)
    discogs._table.item(0, _COL_TITLE).setText("New A")
    assert discogs._on_confirm()
    assert asked == []
    assert label_store.get_record(record.id) == record


def test_unchecked_edited_rows_do_not_count(app, monkeypatch, message_boxes):
    record = _add()
    _linked_queue(record)
    dlg = _editor()
    dlg._table.item(0, _COL_TITLE).setText("New A")
    dlg._table.item(0, 0).setCheckState(Qt.CheckState.Unchecked)
    asked = _answer_sync(monkeypatch, dlg, True)
    assert dlg._on_confirm()
    assert asked == []
    assert label_store.get_record(record.id) == record


@pytest.mark.parametrize("b_row_first", [False, True])
def test_conflicting_a_and_b_edits_the_later_row_wins(app, monkeypatch, message_boxes,
                                                      b_row_first):
    record = _add()
    rows = queue_rows_for_sides(record, "AB")
    label_store.append_to_queue(list(reversed(rows)) if b_row_first else rows)
    dlg = _editor()
    first_row, last_row = 0, 1
    dlg._table.item(first_row, _COL_ARTIST).setText("Edited first")
    dlg._table.item(last_row, _COL_ARTIST).setText("Edited last")
    dlg._table.item(first_row, 3).setText("Only first changed the label")
    asked = _answer_sync(monkeypatch, dlg, True)
    assert dlg._on_confirm()
    assert asked == [2]
    stored = label_store.get_record(record.id)
    # The row edited last in the table order wins; a field only one row changed
    # comes from that row
    assert stored.artist == "Edited last"
    assert stored.label == "Only first changed the label"
    assert (stored.title_a, stored.title_b) == ("Song A", "Song B")


def test_record_with_rows_field_by_field():
    record = _record()
    rows = queue_rows_for_sides(record, "AB")
    rows[0].artist, rows[0].title = "X", "New A"
    rows[1].artist, rows[1].year = "Z", "1970"
    result = record_with_rows(record, rows)
    assert (result.artist, result.year, result.title_a, result.title_b) == (
        "Z", "1970", "New A", "Song B",
    )
    assert record_with_rows(record, list(reversed(rows))).artist == "X"
    assert record.artist == "The Band"                     # the input is not changed


def test_collection_update_is_in_the_queue_transaction(app, monkeypatch, message_boxes):
    record = _add()
    _linked_queue(record)
    dlg = _editor()
    dlg._table.item(0, _COL_TITLE).setText("New A")
    dlg._add_empty_row()
    dlg._table.item(2, _COL_TITLE).setText("New row")
    dlg._table.item(2, _COL_SIDE).setText("A")
    _answer_sync(monkeypatch, dlg, True)

    def failing_insert(*args, **kwargs):
        raise sqlite3.OperationalError("disk I/O error")

    with monkeypatch.context() as patch:
        patch.setattr(label_store, "_insert", failing_insert)
        assert not dlg._on_confirm()
    assert message_boxes[-1][0] == "critical"
    assert label_store.get_record(record.id).title_a == "Song A"
    assert [row[0] for row in _queue()] == ["Song A", "Song B"]


def test_changing_the_side_removes_the_link(app, monkeypatch, message_boxes):
    record = _add()
    _linked_queue(record)
    dlg = _editor()
    dlg._table.item(1, _COL_SIDE).setText("A")             # the B row now prints as A
    dlg._table.item(0, _COL_SIDE).setText("Side a")        # still side A: stays linked
    asked = _answer_sync(monkeypatch, dlg, True)
    assert dlg._on_confirm()
    assert asked == []                                     # the unlinked row is no edit
    assert _queue() == [
        ("Song A", "The Band", "A", record.id, "A"),
        ("Song B", "The Band", "A", None, None),
    ]
    assert label_store.get_record(record.id) == record


def test_side_change_of_a_new_collection_row_follows_the_side(app, message_boxes):
    from ui.entry_dialog import EntryInput, entry_records

    dlg = ReviewDialog([], collection=True)
    dlg.add_entry_rows(entry_records(EntryInput(**_SHARED, title_a="Only")), True)
    dlg._table.item(0, _COL_SIDE).setText("B")
    assert dlg._on_confirm()
    [stored] = label_store.list_records()
    assert (stored.title_a, stored.title_b) == ("", "Only")
    assert _queue() == [("Only", "The Band", "B", stored.id, "B")]


# ── Sync: collection → queue ──────────────────────────────────────────────────

def _edit_in_dialog(monkeypatch, record: CollectionRecord, answer: bool) -> tuple:
    dlg = CollectionDialog()
    asked: list[int] = []
    emitted: list[bool] = []
    dlg.queue_changed.connect(lambda: emitted.append(True))
    monkeypatch.setattr(dlg, "_edit_record", lambda current: record)
    monkeypatch.setattr(dlg, "_ask_update_queue", lambda n: asked.append(n) or answer)
    dlg.edit_record_id(record.id)
    return asked, emitted


def test_record_edit_updates_linked_queue_rows(app, monkeypatch, message_boxes):
    record = _add()
    other = _add(artist="Other")
    _linked_queue(record, extra=True)
    label_store.append_to_queue(queue_rows_for_sides(other, "A"))

    edited = label_store.get_record(record.id)
    edited.title_b, edited.artist = "Better B", "Renamed"
    asked, emitted = _edit_in_dialog(monkeypatch, edited, True)
    assert asked == [2] and emitted == [True]
    assert label_store.get_record(record.id).artist == "Renamed"
    assert _queue() == [
        ("Song A", "Renamed", "A", record.id, "A"),
        ("Better B", "Renamed", "B", record.id, "B"),
        ("One-off", "X", "A", None, None),
        ("Song A", "Other", "A", other.id, "A"),
    ]


def test_record_edit_without_queue_update(app, monkeypatch, message_boxes):
    record = _add()
    _linked_queue(record)
    edited = label_store.get_record(record.id)
    edited.title_a = "Better A"
    asked, emitted = _edit_in_dialog(monkeypatch, edited, False)
    assert asked == [1] and emitted == []
    assert label_store.get_record(record.id).title_a == "Better A"
    assert _queue()[0][0] == "Song A"


def test_record_edit_asks_only_for_rows_that_change(app, monkeypatch, message_boxes):
    record = _add()
    _linked_queue(record)
    edited = label_store.get_record(record.id)
    edited.title_b = ""                                     # the B row keeps its title
    asked, emitted = _edit_in_dialog(monkeypatch, edited, True)
    assert asked == [] and emitted == []
    assert _queue()[1] == ("Song B", "The Band", "B", record.id, "B")

    edited.year = "1970"
    asked, emitted = _edit_in_dialog(monkeypatch, edited, True)
    assert asked == [2] and emitted == [True]
    assert [r.year for r in label_store.load_queue()] == ["1970", "1970"]
    assert [r.title for r in label_store.load_queue()] == ["Song A", "Song B"]


def test_main_window_reloads_the_queue_after_a_record_edit(app, monkeypatch, message_boxes):
    from ui.app import MainWindow

    record = _add()
    _linked_queue(record)

    def fake_exec(dlg):
        edited = label_store.get_record(record.id)
        edited.title_a = "Changed"
        label_store.update_record(edited, sync_queue=True)
        dlg.queue_changed.emit()
        return QDialog.DialogCode.Rejected

    monkeypatch.setattr(CollectionDialog, "exec", fake_exec)
    window = MainWindow()
    assert window._records[0].title == "Song A"
    window.on_load_data()
    assert window._records[0].title == "Changed"


# ── Collection CSV: format ────────────────────────────────────────────────────

def test_collection_csv_english_header(tmp_path):
    path = tmp_path / "in.csv"
    path.write_text(
        "Artist;Label;Country;Year;CatNo;TitleA;TitleB;PrintedA;PrintedB\n"
        "The Band;Label;UK;1969;R 1;Song A;Song B;2026-03-04;\n"
        ";;;;;;;;\n"
        "Nobody;L;;;;;;2026-01-01;\n"
        "Solo;;;;;;Only B;;04.03.2026\n",
        encoding="utf-8",
    )
    result = read_collection_csv(path)
    assert result.skipped == 1 and result.delimiter == ";"
    assert result.records == [_record(), _record(
        artist="Solo", label="", country="", year="", catno="", title_a="", title_b="Only B",
    )]
    assert (result.records[0].printed_a_at, result.records[0].printed_b_at) == (
        "2026-03-04", None,
    )
    assert result.records[1].printed_b_at == "2026-03-04"


@pytest.mark.parametrize("artist", ["Künstler", "Interpret", "Kuenstler"])
def test_collection_csv_german_header_cp1252(tmp_path, artist):
    path = tmp_path / "in.csv"
    path.write_bytes(
        (f"Titel B,Gedruckt A,{artist},Label,Land,Jahr,Katalognummer,Titel A,Gedruckt B\n"
         "Über B,2026-02-01,Mötley,L,DE,1980,K 1,Ä A,kaputt\n").encode("cp1252")
    )
    result = read_collection_csv(path)
    assert result.encoding == "cp1252" and result.delimiter == ","
    [record] = result.records
    assert record == CollectionRecord(
        artist="Mötley", label="L", country="DE", year="1980", catno="K 1",
        title_a="Ä A", title_b="Über B",
    )
    assert (record.printed_a_at, record.printed_b_at) == ("2026-02-01", None)


def test_collection_csv_bom_and_errors(tmp_path):
    path = tmp_path / "bom.csv"
    path.write_bytes("﻿Interpret\tTitel A\nÄrzte\tSong\n".encode("utf-8"))
    result = read_collection_csv(path)
    assert result.encoding == "utf-8-sig"
    assert (result.records[0].artist, result.records[0].title_a) == ("Ärzte", "Song")

    path.write_text("Title;Artist;Side\nSong;X;A\n", encoding="utf-8")   # a queue CSV
    with pytest.raises(CsvImportError) as exc:
        read_collection_csv(path)
    assert exc.value.reason == "no_title" and "Title, Artist, Side" in exc.value.detail
    path.write_text("", encoding="utf-8")
    with pytest.raises(CsvImportError) as exc:
        read_collection_csv(path)
    assert exc.value.reason == "empty"
    # The collection's columns do not change the queue import
    assert csv_io.parse_csv_text("TitleA;Title;Side\nx;Song;B\n").records == [
        LabelRecord("Song", "", "", "", "", "B"),
    ]


def test_collection_csv_export_format(tmp_path):
    stamp = datetime(2026, 3, 4, 12, 0, tzinfo=timezone.utc).isoformat()
    path = tmp_path / "out.csv"
    write_collection_csv(path, [_record(printed_a_at=stamp), _record(title_a="Ä")])
    data = path.read_bytes()
    assert data.startswith(b"\xef\xbb\xbf")
    lines = data.decode("utf-8-sig").splitlines()
    local_day = printed_date(stamp).isoformat()
    assert lines == [
        "Artist;Label;Country;Year;CatNo;TitleA;TitleB;PrintedA;PrintedB",
        f"The Band;Label;UK;1969;R 1;Song A;Song B;{local_day};",
        "The Band;Label;UK;1969;R 1;Ä;Song B;;",
    ]
    assert default_collection_export_name(date(2026, 10, 22)) == "vinyl-collection-2026-10-22.csv"


# ── Collection CSV: import into labels.db ─────────────────────────────────────

def test_duplicate_key():
    assert duplicate_key(_record(artist=" the band ", catno="r 1", title_a="x")) == \
        duplicate_key(_record())
    assert duplicate_key(_record(catno="")) == duplicate_key(
        _record(catno="", artist="THE BAND", title_a=" song a", label="Other")
    )
    assert duplicate_key(_record(catno="")) != duplicate_key(_record(catno="", title_b=""))
    assert duplicate_key(_record()) != duplicate_key(_record(catno=""))


def test_import_records_skip_and_duplicates_within_the_file():
    existing = _add()
    rows = [
        _record(artist="the band", catno=" r 1", title_a="Other title"),  # existing
        _record(artist="New", catno="", title_a="X", title_b="Y"),
        _record(artist="NEW", catno="", title_a="x ", title_b="y"),       # in the file
        _record(artist="Newer", catno="N 1"),
    ]
    assert label_store.count_duplicates(rows) == 2
    result = label_store.import_records(rows, update_existing=False)
    assert (result.imported, result.updated, result.unchanged, result.skipped) == (2, 0, 0, 2)
    assert label_store.get_record(existing.id) == existing
    assert sorted(r.artist for r in label_store.list_records()) == ["New", "Newer", "The Band"]


def test_import_records_update_existing():
    existing = _add()
    label_store.mark_records_printed([existing.id])
    printed_before = _printed(existing.id)
    rows = [
        CollectionRecord(artist="The Band", catno="R 1", label="New label",
                         title_a="New A", title_b="", printed_b_at="2020-05-06"),
        CollectionRecord(artist="New", title_a="X", printed_a_at="2021-01-02"),
        CollectionRecord(artist="new", title_a="x", country="FR"),   # updates the row above
    ]
    result = label_store.import_records(rows, update_existing=True)
    assert (result.imported, result.updated, result.unchanged, result.skipped) == (1, 2, 0, 0)
    stored = label_store.get_record(existing.id)
    assert (stored.label, stored.title_a, stored.title_b, stored.year) == (
        "New label", "New A", "", "",
    )
    # Printed dates only where the CSV has one
    assert stored.printed_a_at == printed_before[0]
    assert stored.printed_b_at == "2020-05-06"
    [new] = [r for r in label_store.list_records() if r.artist == "new"]
    assert (new.country, new.printed_a_at) == ("FR", "2021-01-02")


def test_import_records_is_one_transaction(monkeypatch):
    _add()
    real_insert = label_store._insert_record
    calls = []

    def failing_second_insert(*args, **kwargs):
        calls.append(1)
        if len(calls) == 2:
            raise sqlite3.OperationalError("disk I/O error")
        return real_insert(*args, **kwargs)

    with monkeypatch.context() as patch, pytest.raises(sqlite3.OperationalError):
        patch.setattr(label_store, "_insert_record", failing_second_insert)
        label_store.import_records(
            [_record(artist="One"), _record(artist="Two")], update_existing=True
        )
    assert len(calls) == 2
    assert label_store.record_count() == 1


def test_export_import_round_trip_leaves_the_collection_unchanged(app, monkeypatch,
                                                                  message_boxes, tmp_path):
    _add()
    _add(artist="Ärzte", catno="", title_b="", label="", country="DE")
    printed = _add(artist="Printed", catno="P 1")
    label_store.mark_sides_printed([(printed.id, "B")])
    label_store.import_records(
        [CollectionRecord(artist="From CSV", title_a="T", printed_a_at="2020-01-02")], False
    )

    def snapshot():
        return [
            (asdict(r), r.id, r.printed_a_at, r.printed_b_at, r.created_at, r.updated_at)
            for r in label_store.list_records()
        ]

    before = snapshot()
    dlg = CollectionDialog()
    dlg._chk_unprinted.setChecked(True)                    # export ignores the filter
    path = tmp_path / "collection.csv"
    assert dlg.export_csv(path)
    assert message_boxes[-1] == (
        "information", f"4 record(s) exported:\n{path}",
    )
    monkeypatch.setattr(dlg, "_ask_duplicates", lambda n: "update")
    assert dlg.import_csv(path)
    assert snapshot() == before
    assert message_boxes[-1] == (
        "information",
        "0 record(s) imported, 0 updated, 0 skipped.\n4 record(s) were already up to date.",
    )


def test_round_trip_with_duplicates_inside_the_collection(tmp_path):
    """Two records with the same artist and catalog number survive a round trip."""
    older = _add(title_a="Older")
    newer = _add(title_a="Newer", label="Other")
    label_store.mark_sides_printed([(newer.id, "A")])
    before = label_store.list_records()
    path = tmp_path / "collection.csv"
    write_collection_csv(path, before)
    rows = read_collection_csv(path).records
    assert label_store.count_duplicates(rows) == 2
    result = label_store.import_records(rows, update_existing=True)
    assert (result.imported, result.updated, result.unchanged) == (0, 0, 2)
    after = label_store.list_records()
    assert [(r, r.printed_a_at, r.updated_at) for r in after] == [
        (r, r.printed_a_at, r.updated_at) for r in before
    ]
    assert {older.id, newer.id} == {r.id for r in after}


def test_collection_dialog_import_asks_once_and_reports(app, monkeypatch,
                                                         message_boxes, tmp_path):
    existing = _add()
    path = tmp_path / "in.csv"
    path.write_text(
        "Artist;CatNo;TitleA;TitleB\n"
        "The Band;R 1;Changed A;Song B\n"
        "Fresh;F 1;New;\n"
        "fresh;f 1;Again;\n"
        "No title;X 1;;\n",
        encoding="utf-8",
    )
    dlg = CollectionDialog()
    asked: list[int] = []

    monkeypatch.setattr(dlg, "_ask_duplicates", lambda n: asked.append(n) or None)
    assert not dlg.import_csv(path)                        # cancelled: nothing written
    assert label_store.record_count() == 1

    monkeypatch.setattr(dlg, "_ask_duplicates", lambda n: asked.append(n) or "skip")
    assert dlg.import_csv(path)
    assert asked == [2, 2]
    assert message_boxes[-1] == ("information", "1 record(s) imported, 0 updated, 3 skipped.")
    assert label_store.get_record(existing.id) == existing
    assert dlg._table.rowCount() == 2

    monkeypatch.setattr(dlg, "_ask_duplicates", lambda n: asked.append(n) or "update")
    assert dlg.import_csv(path)
    assert asked == [2, 2, 3]
    # "Fresh / New" is the record of the previous import: already up to date
    assert message_boxes[-1] == (
        "information",
        "0 record(s) imported, 2 updated, 1 skipped.\n1 record(s) were already up to date.",
    )
    assert label_store.get_record(existing.id).title_a == "Changed A"
    # The fields are taken over as written in the file
    assert [(r.artist, r.catno, r.title_a) for r in label_store.list_records()
            if r.id != existing.id] == [("fresh", "f 1", "Again")]


def test_collection_dialog_import_without_duplicates_does_not_ask(app, monkeypatch,
                                                                    message_boxes, tmp_path):
    path = tmp_path / "in.csv"
    path.write_text("Künstler;Titel A\nOne;A\nTwo;B\n", encoding="utf-8")
    dlg = CollectionDialog()
    monkeypatch.setattr(dlg, "_ask_duplicates", lambda n: pytest.fail("asked"))
    assert dlg.import_csv(path)
    assert label_store.record_count() == 2
    assert dlg._stack.currentIndex() == 0

    path.write_text("Title;Side\nx;A\n", encoding="utf-8")
    assert not dlg.import_csv(path)
    assert message_boxes[-1][0] == "warning"
    assert "TitleA" in message_boxes[-1][1]


# ── Queue editor CSV import with "Also save to collection" ────────────────────

def test_queue_csv_import_links_duplicates_to_existing_records(app, monkeypatch,
                                                                message_boxes, tmp_path):
    existing = _add()
    csv_file = tmp_path / "in.csv"
    csv_file.write_text(
        "Title;Artist;Label;Country;Year;Side;CatNo\n"
        "Song A;the band;Label;UK;1969;A;r 1\n"           # existing record (artist + catno)
        "Song B;The Band;Label;UK;1969;B;R 1\n"
        "New A;Fresh;L;UK;1970;A;F 1\n"                   # new record ...
        "New B;FRESH;L;UK;1970;B;F 1\n"                   # ... its B side, own group
        "Lone;Solo;L;UK;1971;A;\n",                       # new, no catno
        encoding="utf-8",
    )
    settings.set_save_to_collection(True)
    dlg = ReviewDialog([], collection=True)
    assert dlg.import_csv(csv_file)
    assert message_boxes[-1] == (
        "information",
        "5 entries imported, 0 skipped (no title).\n"
        "On save, 2 record(s) will be created in the collection.\n"
        "2 row(s) will be linked to existing records of the collection.",
    )
    asked = _answer_sync(monkeypatch, dlg, False)
    assert dlg._on_confirm()
    assert asked == [1]                                    # "the band" differs from the record
    records = {r.artist: r for r in label_store.list_records()}
    assert set(records) == {"The Band", "Fresh", "Solo"}
    assert records["The Band"] == existing
    assert (records["Fresh"].title_a, records["Fresh"].title_b) == ("New A", "New B")
    assert [(r.title, r.record_id, r.record_side) for r in label_store.load_queue()] == [
        ("Song A", existing.id, "A"), ("Song B", existing.id, "B"),
        ("New A", records["Fresh"].id, "A"), ("New B", records["Fresh"].id, "B"),
        ("Lone", records["Solo"].id, "A"),
    ]


def test_queue_csv_import_only_links_without_question(app, monkeypatch, message_boxes,
                                                      tmp_path):
    existing = _add()
    csv_file = tmp_path / "in.csv"
    csv_file.write_text(
        "Title;Artist;Label;Country;Year;Side;CatNo\n"
        "Song A;The Band;Label;UK;1969;A;R 1\n",
        encoding="utf-8",
    )
    settings.set_save_to_collection(True)
    dlg = ReviewDialog([], collection=True)
    assert dlg.import_csv(csv_file)
    assert message_boxes[-1] == (
        "information",
        "1 entries imported, 0 skipped (no title).\n"
        "1 row(s) will be linked to existing records of the collection.",
    )
    asked = _answer_sync(monkeypatch, dlg, True)
    assert dlg._on_confirm()
    assert asked == []                                     # identical data: nothing to sync
    assert label_store.record_count() == 1
    assert [(r.record_id, r.record_side) for r in label_store.load_queue()] == [
        (existing.id, "A"),
    ]


# ── Texts of the questions ────────────────────────────────────────────────────

@pytest.mark.parametrize("language, key, expected", [
    ("DE", "printed_ask_msg", "Die 3 Etiketten aus der Sammlung als gedruckt markieren?"),
    ("EN", "printed_ask_msg", "Mark the 3 labels from the collection as printed?"),
    ("DE", "review_sync_msg", "3 geänderte Einträge gehören zu Platten in der Sammlung. "
                              "Änderungen auch in der Sammlung übernehmen?"),
    ("EN", "review_sync_msg", "3 changed entries belong to records in the collection. "
                              "Apply the changes to the collection too?"),
    ("EN", "review_sync_collection", "Update collection"),
    ("EN", "review_sync_queue_only", "Only the print queue"),
    ("DE", "collection_sync_queue_msg",
     "Auch die 3 Einträge in der Druckwarteschlange aktualisieren?"),
    ("EN", "collection_sync_queue_msg", "Also update the 3 entries in the print queue?"),
    ("EN", "collection_csv_dup_skip", "Skip"),
    ("EN", "collection_csv_dup_update", "Update existing"),
])
def test_question_texts(language, key, expected):
    from modules.i18n import t

    set_language(language)
    try:
        assert t(key, n=3) == expected
    finally:
        set_language("EN")

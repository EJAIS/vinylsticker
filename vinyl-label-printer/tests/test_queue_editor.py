"""
The print queue editor: "Add entry" form logic, saving to labels.db, the empty
queue, unsaved changes, the Discogs import mode and CSV import / export.
"""

from __future__ import annotations

from dataclasses import asdict

import pytest
from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox

from modules import label_store
from modules.i18n import set_language
from modules.records import LabelRecord
from ui.entry_dialog import EntryDialog, EntryInput, entry_records, validate_entry
from ui.review_widget import ReviewDialog
from ui.theme_manager import ThemeManager

_SHARED = dict(artist="The Band", label="Label", country="UK", year="1969", catno="R 1")


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance() or QApplication([])
    set_language("EN")
    ThemeManager.instance().set_setting("dark", persist=False)
    yield application


@pytest.fixture(autouse=True)
def delete_windows(app):
    """Delete the windows a test left open, so later tests never see them."""
    yield
    for widget in app.topLevelWidgets():
        widget.hide()            # not close(): no "unsaved changes" question
        widget.deleteLater()
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete.value)
    app.processEvents()


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


def _queue_titles() -> list[str]:
    return [r.title for r in label_store.load_queue()]


def _open_queue_editor() -> ReviewDialog:
    return ReviewDialog([asdict(r) for r in label_store.load_queue()])


# ── Add entry form ────────────────────────────────────────────────────────────

def test_entry_side_a_only():
    records = entry_records(EntryInput(**_SHARED, title_a="Song A"))
    assert [(r.title, r.side) for r in records] == [("Song A", "A")]
    assert (records[0].artist, records[0].year, records[0].catno) == ("The Band", "1969", "R 1")
    assert records[0].source == label_store.SOURCE_MANUAL


def test_entry_side_b_only():
    records = entry_records(EntryInput(**_SHARED, title_b="Song B"))
    assert [(r.title, r.side) for r in records] == [("Song B", "B")]


def test_entry_sides_a_and_b_share_the_fields():
    records = entry_records(EntryInput(**_SHARED, title_a="Song A", title_b="Song B"))
    assert [(r.title, r.side) for r in records] == [("Song A", "A"), ("Song B", "B")]
    for rec in records:
        assert (rec.artist, rec.label, rec.country, rec.year, rec.catno) == (
            "The Band", "Label", "UK", "1969", "R 1",
        )


@pytest.mark.parametrize(
    ("entry", "error"),
    [
        (EntryInput(**_SHARED), "entry_err_no_title"),
        (EntryInput(title_a="x", year="69"), "entry_err_year"),
        (EntryInput(title_a="x", year="19x9"), "entry_err_year"),
        (EntryInput(title_a="x", year="19690"), "entry_err_year"),
        (EntryInput(title_a="x", year=""), None),
        (EntryInput(title_b="x", year="1969"), None),
    ],
)
def test_entry_validation(entry, error):
    assert validate_entry(entry) == error


def test_entry_dialog_add_and_next(app):
    dlg = EntryDialog()
    added: list[list[LabelRecord]] = []
    dlg.entries_added.connect(added.append)

    dlg.set_entry(EntryInput(**_SHARED, title_a=" Song A ", title_b="Song B"))
    dlg._on_add_next()
    assert [[(r.title, r.side) for r in batch] for batch in added] == [
        [("Song A", "A"), ("Song B", "B")],
    ]
    assert dlg.entry() == EntryInput()                     # form cleared
    assert dlg.focusWidget() is dlg._edit_artist           # focus on the first field
    assert dlg.result() == 0                               # still open

    dlg._on_add()                                          # empty: rejected
    assert len(added) == 1
    assert dlg._lbl_message.text() == "Please enter at least one title (side A or B)."

    dlg.set_entry(EntryInput(title_b="Song C", year="1970"))
    dlg._on_add()
    assert [(r.title, r.side) for r in added[1]] == [("Song C", "B")]
    assert dlg.result() == QDialog.DialogCode.Accepted


# ── Saving the queue ──────────────────────────────────────────────────────────

def test_open_empty_queue_add_entries_and_save(app, message_boxes):
    dlg = _open_queue_editor()
    assert dlg._table.rowCount() == 0
    assert dlg._btn_confirm.isEnabled()
    assert not dlg.has_unsaved_changes()

    dlg._append_records(entry_records(EntryInput(**_SHARED, title_a="A1", title_b="B1")),
                        label_store.SOURCE_MANUAL)
    assert dlg._table.rowCount() == 2
    assert dlg._table.item(0, 0).checkState() == Qt.CheckState.Checked
    assert dlg.has_unsaved_changes()
    assert _queue_titles() == []                     # nothing written yet

    assert dlg._on_confirm()
    queue = label_store.load_queue()
    assert [(r.title, r.side, r.artist) for r in queue] == [
        ("A1", "A", "The Band"), ("B1", "B", "The Band"),
    ]
    assert message_boxes == []


def test_only_checked_rows_are_saved_and_ids_kept(app, message_boxes):
    label_store.replace_queue([
        LabelRecord(t, "X", "", "", "", "A") for t in ("one", "two", "three")
    ])
    ids = [r.id for r in label_store.load_queue()]
    dlg = _open_queue_editor()
    dlg._table.item(1, 0).setCheckState(Qt.CheckState.Unchecked)
    dlg._table.item(2, 1).setText("three edited")
    assert dlg._on_confirm()

    queue = label_store.load_queue()
    assert [r.title for r in queue] == ["one", "three edited"]
    assert [r.id for r in queue] == [ids[0], ids[2]]


def test_saving_nothing_checked_empties_the_queue_after_confirmation(app, monkeypatch):
    label_store.replace_queue([LabelRecord("one", "", "", "", "", "A")])
    asked: list[int] = []

    dlg = _open_queue_editor()
    dlg._set_all_checked(False)
    monkeypatch.setattr(dlg, "_confirm_clear", lambda n: asked.append(n) or False)
    assert not dlg._on_confirm()
    assert _queue_titles() == ["one"]

    monkeypatch.setattr(dlg, "_confirm_clear", lambda n: asked.append(n) or True)
    assert dlg._on_confirm()
    assert _queue_titles() == []
    assert asked == [1, 1]

    # Already empty: saves without asking
    dlg = _open_queue_editor()
    monkeypatch.setattr(dlg, "_confirm_clear", lambda n: pytest.fail("asked"))
    assert dlg._on_confirm()


def test_unsaved_changes_save_discard_cancel(app, monkeypatch, message_boxes):
    label_store.replace_queue([LabelRecord("one", "", "", "", "", "A")])

    def editor_with_change(choice):
        dlg = _open_queue_editor()
        dlg.show()
        dlg._table.item(0, 1).setText("changed")
        monkeypatch.setattr(dlg, "_ask_unsaved", lambda: choice)
        dlg.reject()
        return dlg

    dlg = editor_with_change(None)                  # cancel: keep editing
    assert dlg.isVisible()
    assert _queue_titles() == ["one"]
    dlg._table.item(0, 1).setText("one")            # undone by hand: nothing to ask
    monkeypatch.setattr(dlg, "_ask_unsaved", lambda: pytest.fail("asked"))
    dlg.reject()
    assert not dlg.isVisible()

    dlg = editor_with_change("discard")
    assert not dlg.isVisible()
    assert dlg.result() == QDialog.DialogCode.Rejected
    assert _queue_titles() == ["one"]

    dlg = editor_with_change("save")
    assert not dlg.isVisible()
    assert dlg.result() == QDialog.DialogCode.Accepted
    assert _queue_titles() == ["changed"]


def test_rows_without_title_are_not_saved(app, monkeypatch, message_boxes):
    dlg = _open_queue_editor()
    dlg._append_records([LabelRecord("ok", "", "", "", "", "A")], "manual")
    dlg._add_empty_row()
    dlg._table.item(1, 2).setText("artist only")
    # Accept the "incomplete entries" warning
    monkeypatch.setattr(QMessageBox, "exec", lambda self: None)
    monkeypatch.setattr(QMessageBox, "clickedButton", lambda self: self.buttons()[0])
    assert dlg._on_confirm()
    assert _queue_titles() == ["ok"]


# ── Discogs import mode ───────────────────────────────────────────────────────

@pytest.mark.parametrize(("choice", "expected"), [
    ("append", ["old", "new 1", "new 2"]),
    ("replace", ["new 1", "new 2"]),
    (None, ["old"]),
])
def test_import_mode_append_or_replace(app, monkeypatch, message_boxes, choice, expected):
    label_store.replace_queue([LabelRecord("old", "", "", "", "", "A")])
    rows = [dict(title=f"new {i}", artist="X", side="A") for i in (1, 2)]
    dlg = ReviewDialog(rows, import_mode=True, import_source=label_store.SOURCE_DISCOGS)
    assert dlg.has_unsaved_changes()                # imported rows are not saved yet
    asked: list[int] = []
    monkeypatch.setattr(dlg, "_ask_append_or_replace", lambda n: asked.append(n) or choice)

    assert dlg._on_confirm() == (choice is not None)
    assert asked == [1]
    queue = label_store.load_queue()
    assert [r.title for r in queue] == expected
    assert {r.source for r in queue if r.title.startswith("new")} <= {"discogs"}


def test_import_mode_still_needs_checked_rows(app, message_boxes):
    dlg = ReviewDialog([dict(title="x", side="A")], import_mode=True)
    dlg._set_all_checked(False)
    assert not dlg._btn_confirm.isEnabled()
    assert not dlg._on_confirm()
    assert message_boxes == [("information", "No rows selected.")]


# ── CSV in the editor ─────────────────────────────────────────────────────────

def test_csv_export_import_round_trip_through_the_editor(app, monkeypatch, message_boxes,
                                                         tmp_path):
    label_store.replace_queue([
        LabelRecord("One; two", "Ärtist", "L", "DE", "1970", "A", "C-1"),
        LabelRecord("Three", "", "", "", "", "B", ""),
    ])
    dlg = _open_queue_editor()
    dlg._append_records([LabelRecord("Unchecked", "", "", "", "", "A")], "manual")
    dlg._table.item(2, 0).setCheckState(Qt.CheckState.Unchecked)
    dlg._search.setText("one")                      # filter hides rows 1 and 2
    before = [dlg._row_to_labelrecord(r) for r in range(dlg._table.rowCount())]

    out = tmp_path / "export.csv"
    assert dlg.export_csv(out)                      # every row, also hidden / unchecked
    assert message_boxes[-1][0] == "information"

    other = _open_queue_editor()
    monkeypatch.setattr(other, "_ask_append_or_replace", lambda n: "replace")
    assert other.import_csv(out)
    after = [other._row_to_labelrecord(r) for r in range(other._table.rowCount())]
    assert after == before
    assert message_boxes[-1] == ("information", "3 entries imported, 0 skipped (no title).")
    assert {other._read_row(r)["source"] for r in range(3)} == {"csv"}
    assert _queue_titles() == ["One; two", "Three"]  # nothing written before confirm


def test_csv_import_append_and_report_skipped(app, monkeypatch, message_boxes, tmp_path):
    csv_file = tmp_path / "in.csv"
    csv_file.write_text("Titel;Interpret\nNew;X\n;no title\n", encoding="utf-8")
    dlg = _open_queue_editor()
    dlg._append_records([LabelRecord("Existing", "", "", "", "", "A")], "manual")
    monkeypatch.setattr(dlg, "_ask_append_or_replace", lambda n: "append")

    assert dlg.import_csv(csv_file)
    assert [dlg._read_row(r)["title"] for r in range(dlg._table.rowCount())] == [
        "Existing", "New",
    ]
    assert message_boxes[-1] == ("information", "1 entries imported, 1 skipped (no title).")


def test_csv_import_error_is_reported(app, message_boxes, tmp_path):
    csv_file = tmp_path / "bad.csv"
    csv_file.write_text("Song,Artist\nx,y\n", encoding="utf-8")
    dlg = _open_queue_editor()
    assert not dlg.import_csv(csv_file)
    assert message_boxes[-1][0] == "warning"
    assert "Columns found: Song, Artist" in message_boxes[-1][1]
    assert dlg._table.rowCount() == 0


# ── Main window ───────────────────────────────────────────────────────────────

def test_queue_and_local_load_data_open_the_editor_when_empty(app, monkeypatch,
                                                              message_boxes):
    from ui.app import MainWindow

    opened: list[int] = []

    def fake_exec(self):
        opened.append(self._table.rowCount())
        return QDialog.DialogCode.Rejected

    monkeypatch.setattr(ReviewDialog, "exec", fake_exec)
    window = MainWindow()
    window.on_open_queue()
    window.on_load_data()            # LOCAL mode (default)
    assert opened == [0, 0]
    assert message_boxes == []

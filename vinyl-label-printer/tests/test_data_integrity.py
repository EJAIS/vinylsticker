"""
Data integrity fixes from the 1.2 code review: the main window never edits a
stale queue, drag & drop in the queue editor moves whole rows, and
settings.json / credentials.json survive a torn write.

(The collection sync and the printed question are covered in
test_collection_sync.py and test_ux_polish.py.)
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict
from pathlib import Path

import pytest
from PyQt6.QtCore import QEvent, QPointF, Qt
from PyQt6.QtGui import QColor, QDropEvent
from PyQt6.QtWidgets import QAbstractItemView, QApplication, QDialog, QMessageBox

from config import settings
from modules import credentials_manager, json_store, label_store
from modules.credentials_manager import CredentialsManager
from modules.i18n import set_language
from modules.records import CollectionRecord, LabelRecord, queue_rows_for_sides
from ui.collection_dialog import CollectionDialog
from ui.review_widget import ReviewDialog
from ui.theme_manager import ThemeManager, current_colors

_SHARED = dict(artist="The Band", label="Label", country="UK", year="1969", catno="R 1")
_COL_CHECK, _COL_TITLE = 0, 1
_ROLE_RECORD_ID = Qt.ItemDataRole.UserRole + 2
_Indicator = QAbstractItemView.DropIndicatorPosition


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance() or QApplication([])
    set_language("EN")
    yield application


@pytest.fixture(autouse=True)
def settings_file(tmp_path, monkeypatch) -> Path:
    path = tmp_path / "settings.json"
    monkeypatch.setattr(settings, "get_settings_file", lambda: path)
    return path


@pytest.fixture(autouse=True)
def credentials_file(tmp_path, monkeypatch) -> Path:
    path = tmp_path / "credentials.json"
    monkeypatch.setattr(credentials_manager, "get_credentials_file", lambda: path)
    return path


@pytest.fixture(autouse=True)
def no_blocked_files(monkeypatch):
    monkeypatch.setattr(json_store, "_blocked", set())


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
    shown: list[tuple[str, str]] = []
    for name in ("critical", "warning", "information", "question"):
        monkeypatch.setattr(
            QMessageBox, name,
            lambda *args, _name=name, **kwargs: shown.append((_name, args[2])),
        )
    return shown


@pytest.fixture
def window(app, monkeypatch, message_boxes, tmp_path):
    """A main window whose PDF generation and printing do nothing."""
    import ui.app as app_module

    def fake_generate_pdf(records, output_path, **kwargs):
        output_path.write_bytes(b"%PDF-1.4\n")
        return output_path

    monkeypatch.setattr(app_module, "generate_pdf", fake_generate_pdf)
    monkeypatch.setattr(app_module, "print_pdf", lambda path: None)
    monkeypatch.setattr(app_module.PreviewWidget, "load_pdf", lambda self, path: None)
    monkeypatch.setattr(app_module, "get_output_dir", lambda: tmp_path)
    return app_module.MainWindow()


def _one_off(title: str) -> LabelRecord:
    return LabelRecord(title, "X", "", "", "", "A")


def _add_record(**kwargs) -> CollectionRecord:
    fields = dict(_SHARED, title_a="Song A", title_b="Song B")
    fields.update(kwargs)
    return label_store.get_record(label_store.add_record(CollectionRecord(**fields)))


def _queue_titles() -> list[str]:
    return [r.title for r in label_store.load_queue()]


# ── 1. The main window never edits a stale queue ──────────────────────────────

def _save_editor_unchanged(monkeypatch) -> list[list[str]]:
    """Make the queue editor save at once; return the titles it was opened with."""
    opened: list[list[str]] = []

    def fake_exec(dlg):
        opened.append([dlg._table.item(r, _COL_TITLE).text()
                       for r in range(dlg._table.rowCount())])
        return QDialog.DialogCode.Accepted if dlg._on_confirm() else QDialog.DialogCode.Rejected

    monkeypatch.setattr(ReviewDialog, "exec", fake_exec)
    return opened


def test_change_token_import_reloads_the_main_window(window, monkeypatch):
    from ui.discogs_dialog import DiscogsDialog

    label_store.append_to_queue([_one_off("Old")])
    window._load_queue()

    def fake_discogs_exec(dlg):
        # An "Append" import of the Discogs dialog
        label_store.append_to_queue([_one_off("Imported 1"), _one_off("Imported 2")])
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(DiscogsDialog, "exec", fake_discogs_exec)
    footer_updates: list[bool] = []
    monkeypatch.setattr(window, "_update_footer_status", lambda: footer_updates.append(True))
    window.on_open_settings()
    window._settings_dialog._on_change_token()
    assert [r.title for r in window._records] == ["Old", "Imported 1", "Imported 2"]
    assert footer_updates == [True]

    # Opening and saving the queue editor keeps the imported rows
    opened = _save_editor_unchanged(monkeypatch)
    window.on_open_queue()
    assert opened == [["Old", "Imported 1", "Imported 2"]]
    assert _queue_titles() == ["Old", "Imported 1", "Imported 2"]


def test_change_token_without_import_does_not_reload(window, monkeypatch):
    from ui.discogs_dialog import DiscogsDialog

    monkeypatch.setattr(DiscogsDialog, "exec", lambda dlg: QDialog.DialogCode.Rejected)
    window.on_open_settings()
    emitted: list[bool] = []
    window._settings_dialog.queue_changed.connect(lambda: emitted.append(True))
    window._settings_dialog._on_change_token()
    assert emitted == []


def test_queue_editor_starts_from_labels_db(window, monkeypatch):
    """Defense in depth: rows written behind the main window's back survive a save."""
    label_store.append_to_queue([_one_off("Old")])
    window._load_queue()
    label_store.append_to_queue([_one_off("Written elsewhere")])
    opened = _save_editor_unchanged(monkeypatch)
    window.on_open_queue()
    assert opened == [["Old", "Written elsewhere"]]
    assert _queue_titles() == ["Old", "Written elsewhere"]


def test_queue_editor_does_not_open_if_the_queue_cannot_be_read(window, monkeypatch,
                                                                message_boxes):
    opened = _save_editor_unchanged(monkeypatch)

    def failing_load():
        raise OSError("disk gone")

    monkeypatch.setattr(label_store, "load_queue", failing_load)
    window.on_open_queue()
    assert opened == []
    assert message_boxes[-1][0] == "critical"


def test_deleting_a_record_unlinks_the_main_windows_rows(window, monkeypatch, message_boxes):
    record = _add_record()
    label_store.append_to_queue(queue_rows_for_sides(record, "AB"))
    window._load_queue()

    def fake_collection_exec(dlg):
        monkeypatch.setattr(dlg, "_selected_ids", lambda: [record.id])
        monkeypatch.setattr(dlg, "_confirm_delete", lambda ids: True)
        dlg._on_delete()
        return QDialog.DialogCode.Rejected         # closed without "Add to print queue"

    monkeypatch.setattr(CollectionDialog, "exec", fake_collection_exec)
    window.on_load_data()
    assert [r.record_id for r in window._records] == [None, None]
    # The queue editor saves without a foreign key error on the deleted record
    _save_editor_unchanged(monkeypatch)
    window.on_open_queue()
    assert not any(box[0] == "critical" for box in message_boxes)
    assert _queue_titles() == ["Song A", "Song B"]


# ── 2. Drag & drop moves whole rows ───────────────────────────────────────────

class _OwnDropEvent(QDropEvent):
    """A drop from the table itself (a synthetic event has no drag source)."""

    def __init__(self, table, pos: QPointF) -> None:
        mime = table.model().mimeData(table.selectedIndexes())
        super().__init__(
            pos, Qt.DropAction.MoveAction, mime,
            Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
        )
        self._table = table
        self._mime = mime         # keep the mime data alive with the event

    def source(self):
        return self._table


@pytest.fixture
def editor(app, message_boxes):
    """Queue editor with T0 … T4; T1 / T2 are the A / B rows of a record, T3 unchecked."""
    record = _add_record(title_a="T1", title_b="T2")
    a_row, b_row = queue_rows_for_sides(record, "AB")
    label_store.append_to_queue([_one_off("T0"), a_row, b_row, _one_off("T3"), _one_off("T4")])
    dlg = ReviewDialog([asdict(r) for r in label_store.load_queue()], collection=True)
    dlg._table.item(3, _COL_CHECK).setCheckState(Qt.CheckState.Unchecked)
    dlg._saved_state = dlg._table_state()      # start the tests without unsaved changes
    dlg.record = record
    dlg.show()
    return dlg


def _rows(dlg) -> list[tuple[str, bool, int]]:
    """(title, checked, linked record id or -1) per row; asserts no row is empty."""
    table = dlg._table
    result = []
    for row in range(table.rowCount()):
        chk = table.item(row, _COL_CHECK)
        assert chk is not None and chk.flags() & Qt.ItemFlag.ItemIsUserCheckable
        assert all(table.item(row, col) is not None for col in range(table.columnCount()))
        assert table.item(row, _COL_TITLE).text()
        result.append((
            table.item(row, _COL_TITLE).text(),
            chk.checkState() == Qt.CheckState.Checked,
            chk.data(_ROLE_RECORD_ID),
        ))
    return result


def _drop(dlg, monkeypatch, rows: list[int], indicator, target_row: int | None) -> _OwnDropEvent:
    """Select *rows* and drop them on *target_row* (None: below the last row)."""
    table = dlg._table
    table.clearSelection()
    for row in rows:
        table.selectionModel().select(
            table.model().index(row, 0),
            table.selectionModel().SelectionFlag.Select
            | table.selectionModel().SelectionFlag.Rows,
        )
    if target_row is None:
        last = table.rowCount() - 1
        pos = QPointF(20, table.rowViewportPosition(last) + table.rowHeight(last) + 5)
    else:
        pos = QPointF(table.visualRect(table.model().index(target_row, _COL_TITLE)).center())
    # Set by dragMoveEvent during a real drag
    monkeypatch.setattr(table, "dropIndicatorPosition", lambda: indicator)
    event = _OwnDropEvent(table, pos)
    table.dropEvent(event)
    return event


def _selected_rows(dlg) -> list[int]:
    return sorted({index.row() for index in dlg._table.selectedIndexes()})


def _titles(dlg) -> list[str]:
    return [title for title, *_ in _rows(dlg)]


def test_drop_moves_one_row_down(editor, monkeypatch):
    event = _drop(editor, monkeypatch, [0], _Indicator.BelowItem, 2)
    assert _titles(editor) == ["T1", "T2", "T0", "T3", "T4"]
    assert _selected_rows(editor) == [2]
    # Accepted, but not as a move (Qt would remove the selected rows again)
    assert event.isAccepted()
    assert event.dropAction() != Qt.DropAction.MoveAction
    assert editor.has_unsaved_changes()


def test_drop_moves_one_row_up(editor, monkeypatch):
    _drop(editor, monkeypatch, [3], _Indicator.AboveItem, 1)
    rid = editor.record.id
    assert _rows(editor) == [
        ("T0", True, -1), ("T3", False, -1), ("T1", True, rid), ("T2", True, rid),
        ("T4", True, -1),
    ]
    assert _selected_rows(editor) == [1]


def test_drop_moves_several_non_adjacent_rows_in_their_order(editor, monkeypatch):
    _drop(editor, monkeypatch, [0, 2], _Indicator.BelowItem, 3)
    rid = editor.record.id
    assert _rows(editor) == [
        ("T1", True, rid), ("T3", False, -1), ("T0", True, -1), ("T2", True, rid),
        ("T4", True, -1),
    ]
    assert _selected_rows(editor) == [2, 3]


def test_drop_on_the_empty_viewport_moves_to_the_end(editor, monkeypatch):
    _drop(editor, monkeypatch, [1], _Indicator.OnViewport, None)
    assert _titles(editor) == ["T0", "T2", "T3", "T4", "T1"]
    assert _selected_rows(editor) == [4]


@pytest.mark.parametrize("indicator", [_Indicator.AboveItem, _Indicator.BelowItem])
def test_drop_on_its_own_position_changes_nothing(editor, monkeypatch, indicator):
    before = _rows(editor)
    moved: list[list[int]] = []
    editor._table.rows_moved.connect(moved.append)
    _drop(editor, monkeypatch, [2], indicator, 2)
    assert _rows(editor) == before
    assert moved == []
    assert not editor.has_unsaved_changes()


def test_moved_rows_are_saved_in_the_new_order_with_their_links(editor, monkeypatch):
    rid = editor.record.id
    _drop(editor, monkeypatch, [1, 2], _Indicator.OnViewport, None)   # record rows to the end
    _drop(editor, monkeypatch, [3], _Indicator.AboveItem, 0)          # T1 to the top
    assert editor._on_confirm()
    # T3 is unchecked: not saved
    assert [(r.title, r.record_id, r.record_side) for r in label_store.load_queue()] == [
        ("T1", rid, "A"), ("T0", None, None), ("T4", None, None), ("T2", rid, "B"),
    ]


def test_move_keeps_the_validation_tints(editor, monkeypatch):
    ThemeManager.instance().set_setting("dark", persist=False)
    error = QColor(current_colors().cell_error_bg)
    editor._table.item(4, _COL_TITLE).setText("")          # T4 lacks its title now
    _drop(editor, monkeypatch, [4], _Indicator.AboveItem, 0)
    assert editor._table.item(0, _COL_TITLE).text() == ""
    assert editor._table.item(0, _COL_TITLE).background().color() == error
    assert editor._table.item(1, _COL_TITLE).background().style() == Qt.BrushStyle.NoBrush


@pytest.mark.parametrize("language, tip", [
    ("EN", "Clear the search to reorder rows"),
    ("DE", "Zum Verschieben die Suche leeren"),
])
def test_search_filter_blocks_drag_and_drop(editor, language, tip):
    set_language(language)
    try:
        assert editor._table.dragEnabled()
        editor._search.setText("T1")
        assert not editor._table.dragEnabled()
        assert editor._table.toolTip() == tip
        editor._search.setText("")
        assert editor._table.dragEnabled()
        assert editor._table.toolTip() == ""
    finally:
        set_language("EN")


def test_drop_from_another_widget_is_ignored(editor):
    class _ForeignDrop(_OwnDropEvent):
        def source(self):
            return None

    before = _rows(editor)
    event = _ForeignDrop(editor._table, QPointF(20, 5))
    editor._table.dropEvent(event)
    assert not event.isAccepted()
    assert _rows(editor) == before


# ── 5. settings.json / credentials.json survive a torn write ──────────────────

def _corrupt_files(path: Path) -> list[Path]:
    return sorted(path.parent.glob(f"{path.name}.corrupt-*"))


def test_atomic_write_keeps_the_old_content_on_failure(tmp_path, monkeypatch):
    folder = tmp_path / "config"
    folder.mkdir()
    target = folder / "settings.json"
    json_store.write_json(target, {"theme": "dark"})

    def failing_replace(source, destination):
        raise OSError("power failure")

    monkeypatch.setattr(json_store.os, "replace", failing_replace)
    with pytest.raises(OSError):
        json_store.write_json(target, {"theme": "light"})
    assert json.loads(target.read_text(encoding="utf-8")) == {"theme": "dark"}
    assert sorted(p.name for p in folder.iterdir()) == ["settings.json"]   # no temp file


def test_atomic_write_retries_a_briefly_locked_target(tmp_path, monkeypatch):
    target = tmp_path / "settings.json"
    real_replace = os.replace
    attempts: list[int] = []

    def flaky_replace(source, destination):
        attempts.append(1)
        if len(attempts) < 3:
            raise PermissionError("held open by a virus scanner")
        real_replace(source, destination)

    monkeypatch.setattr(json_store.os, "replace", flaky_replace)
    monkeypatch.setattr(json_store.time, "sleep", lambda seconds: None)
    assert json_store.write_json(target, {"language": "EN"})
    assert len(attempts) == 3
    assert json.loads(target.read_text(encoding="utf-8")) == {"language": "EN"}


@pytest.mark.parametrize("broken", ['{"theme": "dark", "watermark_pa', "", "[1, 2]", "\xff"])
def test_broken_settings_are_moved_aside_and_defaults_used(settings_file, caplog, broken):
    settings_file.write_bytes(broken.encode("latin-1"))
    with caplog.at_level(logging.WARNING, logger="vinyl_label_printer"):
        assert settings.get_theme() == "auto"
        assert settings.get_calibration_x() == 0.0
    [moved] = _corrupt_files(settings_file)
    assert moved.read_bytes() == broken.encode("latin-1")
    assert not settings_file.exists()
    assert any(str(moved) in record.getMessage() for record in caplog.records)

    # A later setter starts a new file and leaves the moved one alone
    settings.set_theme("light")
    assert json.loads(settings_file.read_text(encoding="utf-8")) == {"theme": "light"}
    assert _corrupt_files(settings_file) == [moved]
    assert moved.read_bytes() == broken.encode("latin-1")


def test_settings_that_cannot_be_moved_aside_are_never_overwritten(settings_file,
                                                                   monkeypatch):
    settings_file.write_text("{torn", encoding="utf-8")

    def locked(source, destination):
        raise PermissionError("locked")

    monkeypatch.setattr(json_store, "_replace", locked)
    assert settings.get_theme() == "auto"
    settings.set_theme("dark")
    assert settings_file.read_text(encoding="utf-8") == "{torn"
    assert _corrupt_files(settings_file) == []


def test_broken_credentials_are_moved_aside_without_logging_them(credentials_file, caplog):
    secret = '{"discogs_username": "me", "discogs_token": "secret-token-123"'   # torn
    credentials_file.write_text(secret, encoding="utf-8")
    with caplog.at_level(logging.DEBUG, logger="vinyl_label_printer"):
        assert CredentialsManager().load() == {"discogs_username": "", "discogs_token": ""}
        assert not CredentialsManager().are_valid()
    [moved] = _corrupt_files(credentials_file)
    assert moved.read_text(encoding="utf-8") == secret
    assert not any("secret-token" in record.getMessage() for record in caplog.records)
    assert any(str(moved) in record.getMessage() for record in caplog.records)

    CredentialsManager().save("me", "new-token")
    assert CredentialsManager().load() == {"discogs_username": "me", "discogs_token": "new-token"}
    assert _corrupt_files(credentials_file) == [moved]
    assert moved.read_text(encoding="utf-8") == secret


@pytest.mark.skipif(os.name != "posix", reason="file modes are POSIX only")
def test_credentials_stay_owner_only(credentials_file, settings_file):
    CredentialsManager().save("me", "token")
    assert credentials_file.stat().st_mode & 0o777 == 0o600
    settings.set_theme("dark")
    assert settings_file.stat().st_mode & 0o777 == 0o644


def test_messages_from_before_the_log_setup_reach_app_log(settings_file, monkeypatch, caplog):
    # main.py reads settings.json (debug setting) before the log file exists
    monkeypatch.setattr(json_store, "_early_messages", [])
    monkeypatch.setattr(json_store.logger, "hasHandlers", lambda: False)
    settings_file.write_text("{torn", encoding="utf-8")
    assert not settings.get_debug_logging()
    [(level, message)] = json_store._early_messages
    assert level == logging.WARNING and "moved aside" in message

    monkeypatch.undo()
    with caplog.at_level(logging.WARNING, logger="vinyl_label_printer"):
        json_store.log_early_messages()
    assert [record.getMessage() for record in caplog.records] == [message]
    assert json_store._early_messages == []

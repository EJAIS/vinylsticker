"""
UX polish (1.2): the PDF follows the queue, the start position stays until
the user changes it, remembered window geometry and table columns, keyboard
shortcuts, the collection status in the footer (LOCAL mode) and the preview
placeholder.
"""

from __future__ import annotations

import base64
import json

import pytest
from PyQt6.QtCore import QEvent, QRect, Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox, QTableWidget

from config import settings
from config.avery_formats import AVERY_FORMATS
from modules import label_store
from modules.data_source import DataSourceMode
from modules.i18n import set_language
from modules.records import CollectionRecord, LabelRecord, queue_rows_for_sides
from ui import window_state
from ui.collection_dialog import _COL_YEAR, CollectionDialog
from ui.review_widget import ReviewDialog
from ui.shortcuts import is_editing

_SHARED = dict(artist="The Band", label="Label", country="UK", year="1969", catno="R 1")


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance() or QApplication([])
    set_language("EN")
    yield application


@pytest.fixture(autouse=True)
def settings_file(tmp_path, monkeypatch):
    """A fresh settings.json per test (LOCAL mode is the default)."""
    path = tmp_path / "settings.json"
    monkeypatch.setattr(settings, "get_settings_file", lambda: path)
    return path


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


@pytest.fixture
def window(app, monkeypatch, message_boxes, tmp_path):
    """A main window with recorded PDF generation and printing."""
    import ui.app as app_module

    calls = {"pdf_error": None, "print_error": None, "generated": [], "printed": []}

    def fake_generate_pdf(records, output_path, **kwargs):
        if calls["pdf_error"]:
            raise calls["pdf_error"]
        calls["generated"].append(([r.title for r in records], kwargs["start_position"]))
        output_path.write_bytes(b"%PDF-1.4\n" + repr(kwargs).encode())
        return output_path

    def fake_print_pdf(path):
        if calls["print_error"]:
            raise calls["print_error"]
        calls["printed"].append(path)

    def fake_load_pdf(preview, path):
        preview._pages = ["page"]          # rendered pages, never painted here

    output = tmp_path / "output"
    output.mkdir()
    monkeypatch.setattr(app_module, "generate_pdf", fake_generate_pdf)
    monkeypatch.setattr(app_module, "print_pdf", fake_print_pdf)
    monkeypatch.setattr(app_module.PreviewWidget, "load_pdf", fake_load_pdf)
    monkeypatch.setattr(app_module, "get_output_dir", lambda: output)

    win = app_module.MainWindow()
    win.asked = []

    def fake_ask(n_labels):
        win.asked.append(n_labels)
        return True

    monkeypatch.setattr(win, "_ask_mark_printed", fake_ask)
    win.calls = calls
    win.output = output
    return win


def _record(**kwargs) -> CollectionRecord:
    fields = dict(_SHARED, title_a="Song A", title_b="Song B")
    fields.update(kwargs)
    return CollectionRecord(**fields)


def _add(**kwargs) -> CollectionRecord:
    return label_store.get_record(label_store.add_record(_record(**kwargs)))


def _one_off(title: str) -> LabelRecord:
    return LabelRecord(title, "X", "", "", "", "A")


# ── 1. The PDF follows the queue ──────────────────────────────────────────────

def test_no_pdf_on_start_and_regenerated_after_a_queue_change(window):
    label_store.append_to_queue([_one_off("One"), _one_off("Two")])
    window._load_queue()
    assert window.calls["generated"] == []                # never on start / first load
    assert window._pdf_path is None
    assert not window._sidebar.print_enabled()

    window.on_create_pdf()
    assert window.calls["generated"] == [(["One", "Two"], 0)]
    assert window._sidebar.print_enabled()

    window._load_queue()                                  # same content: nothing to do
    assert len(window.calls["generated"]) == 1

    label_store.append_to_queue([_one_off("Three")])
    window._load_queue()
    assert window.calls["generated"][-1] == (["One", "Two", "Three"], 0)
    assert window._sidebar.print_enabled()
    assert window._sidebar.pdf_status() == "done"

    window.on_print()                                     # prints the new labels
    assert window.calls["printed"][-1].read_bytes() == (window.output / "labels.pdf").read_bytes()


def test_queue_editor_and_collection_reload_the_pdf(window, monkeypatch):
    label_store.append_to_queue([_one_off("One")])
    window._load_queue()
    window.on_create_pdf()

    def fake_editor_exec(dlg):
        label_store.replace_queue([_one_off("Edited")])
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(ReviewDialog, "exec", fake_editor_exec)
    window.on_open_queue()
    assert window.calls["generated"][-1] == (["Edited"], 0)

    record = _add()

    def fake_collection_exec(dlg):
        label_store.append_to_queue(queue_rows_for_sides(record, "A"))
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(CollectionDialog, "exec", fake_collection_exec)
    window.on_load_data()
    assert window.calls["generated"][-1] == (["Edited", "Song A"], 0)


def test_empty_queue_clears_preview_and_disables_print(window):
    label_store.append_to_queue([_one_off("One")])
    window._load_queue()
    window.on_create_pdf()
    assert window._preview.has_pages()

    label_store.replace_queue([])
    window._load_queue()
    assert window._pdf_path is None
    assert not window._sidebar.print_enabled()
    assert window._sidebar.pdf_status() == "ready"
    assert not window._preview.has_pages()
    assert window._preview.placeholder_text() == (
        "Choose records from your collection via “Load data”."
    )

    # A PDF was created in this session: a new queue gets one again
    label_store.append_to_queue([_one_off("Again")])
    window._load_queue()
    assert window.calls["generated"][-1] == (["Again"], 0)
    assert window._sidebar.print_enabled()


def test_automatic_regeneration_never_asks_the_printed_question(window):
    record = _add()
    label_store.append_to_queue(queue_rows_for_sides(record, "AB"))
    window._load_queue()
    window.on_create_pdf()
    assert window.asked == []                             # a preview never asks
    window.on_print()
    assert window.asked == [2]

    label_store.append_to_queue(queue_rows_for_sides(record, "A"))
    window._load_queue()                                  # queue change
    window._refresh_pdf_layout()                          # watermark / calibration
    assert len(window.calls["generated"]) == 3
    assert window.asked == [2]

    window.on_print()                                     # explicit: asks for the new queue
    assert window.asked == [2, 3]


def test_failed_automatic_regeneration_disables_print(window, message_boxes):
    label_store.append_to_queue([_one_off("One")])
    window._load_queue()
    window.on_create_pdf()

    window.calls["pdf_error"] = RuntimeError("disk full")
    label_store.append_to_queue([_one_off("Two")])
    window._load_queue()
    assert message_boxes[-1][0] == "critical"
    assert window._pdf_path is None
    assert not window._sidebar.print_enabled()
    window.on_print()                                     # e.g. via a stale shortcut
    assert window.calls["printed"] == []

    # Not retried for the same queue; a later change tries again
    n_boxes = len(message_boxes)
    window._load_queue()
    assert len(message_boxes) == n_boxes
    window.calls["pdf_error"] = None
    label_store.append_to_queue([_one_off("Three")])
    window._load_queue()
    assert window._sidebar.print_enabled()


def test_watermark_or_calibration_change_regenerates_an_existing_pdf(window, monkeypatch):
    monkeypatch.setitem(AVERY_FORMATS["4780"], "calibration_x_mm", 0.0)
    label_store.append_to_queue([_one_off("One")])
    window._load_queue()

    window.on_open_settings()
    dialog = window._settings_dialog
    dialog._spin_cal_x.setValue(0.5)
    assert not window._layout_timer.isActive()            # no PDF yet: nothing to do

    window.on_create_pdf()
    dialog._spin_cal_x.setValue(0.7)
    dialog._spin_cal_x.setValue(0.9)
    assert window._layout_timer.isActive()                # debounced
    window._layout_timer.stop()
    window._refresh_pdf_layout()
    assert len(window.calls["generated"]) == 2


# ── 2. The start position stays until the user changes it ───────────────────

def _set_start(window, index: int) -> None:
    window._start_index = index
    window._update_start_position_text()


def test_start_position_unchanged_after_print_and_create_pdf(window):
    label_store.append_to_queue([_one_off("One")])
    window._load_queue()
    _set_start(window, 12)

    window.on_create_pdf()
    assert window._start_index == 12
    assert window.calls["generated"] == [(["One"], 12)]

    window.calls["print_error"] = RuntimeError("xdg-open failed")
    window.on_print()
    assert window._start_index == 12                      # failed print: kept

    window.calls["print_error"] = None
    window.on_print()
    window.on_print()
    assert window._start_index == 12
    assert window._sidebar.start_position_text() == "Label 13 (R4 C1)"
    assert window.calls["generated"] == [(["One"], 12)]   # Print never regenerates
    # The viewer got a copy of the PDF, not the file itself
    printed = window.calls["printed"][-1]
    assert printed != window.output / "labels.pdf"
    assert b"'start_position': 12" in printed.read_bytes()

    window.on_create_pdf()
    assert window._start_index == 12
    assert window.calls["generated"][-1] == (["One"], 12)


def test_start_position_survives_a_queue_change(window):
    label_store.append_to_queue([_one_off("One")])
    window._load_queue()
    _set_start(window, 12)
    window.on_create_pdf()
    window.on_print()

    label_store.append_to_queue([_one_off("Two")])
    window._load_queue()                                  # automatic regeneration
    assert window.calls["generated"][-1] == (["One", "Two"], 12)
    assert window._start_index == 12
    assert window._sidebar.start_position_text() == "Label 13 (R4 C1)"


def test_start_position_survives_a_mode_and_language_switch(window):
    label_store.append_to_queue([_one_off("One")])
    window._load_queue()
    _set_start(window, 12)

    window.on_mode_changed(DataSourceMode.DISCOGS.value)
    window.on_mode_changed(DataSourceMode.LOCAL.value)
    assert window._start_index == 12
    try:
        window._on_language_changed("DE")
        assert window._start_index == 12
    finally:
        window._on_language_changed("EN")
    assert window._sidebar.start_position_text() == "Label 13 (R4 C1)"

    window.on_create_pdf()
    assert window.calls["generated"][-1] == (["One"], 12)


def test_new_main_window_starts_at_label_1(window):
    import ui.app as app_module

    _set_start(window, 12)
    fresh = app_module.MainWindow()
    assert fresh._start_index == 0
    assert fresh._sidebar.start_position_text() == "Label 1 (R1 C1)"


def test_old_print_copies_are_removed(window):
    label_store.append_to_queue([_one_off("One")])
    window._load_queue()
    window.on_create_pdf()
    for _ in range(8):
        window.on_print()
    assert len(list(window.output.glob("labels-print-*.pdf"))) == 5


# ── 3. Window geometry and table columns ──────────────────────────────────────

def test_geometry_and_header_settings_round_trip(settings_file):
    assert settings.get_window_geometry("main_window") is None
    settings.set_window_geometry("main_window", b"\x01\x02geometry")
    settings.set_header_state("collection_dialog", 11, b"\x00state")
    assert settings.get_window_geometry("main_window") == b"\x01\x02geometry"
    assert settings.get_header_state("collection_dialog") == (11, b"\x00state")
    stored = json.loads(settings_file.read_text())
    assert stored["window_geometry"]["main_window"] == base64.b64encode(
        b"\x01\x02geometry").decode()


@pytest.mark.parametrize("stored", [
    {"window_geometry": "not a dict", "header_state": ["no"]},
    {"window_geometry": {"main_window": "%%% not base64"},
     "header_state": {"collection_dialog": {"columns": 11, "state": "%%%"}}},
    {"window_geometry": {"main_window": 42},
     "header_state": {"collection_dialog": {"columns": "11", "state": "AAAA"}}},
])
def test_invalid_stored_geometry_and_header_are_ignored(settings_file, stored):
    settings_file.write_text(json.dumps(stored))
    assert settings.get_window_geometry("main_window") is None
    assert settings.get_header_state("collection_dialog") is None
    # Saving over invalid data repairs it
    settings.set_window_geometry("main_window", b"ok")
    assert settings.get_window_geometry("main_window") == b"ok"


def test_header_restore_checks_column_count_and_state(app):
    table = QTableWidget(0, 4)
    header = table.horizontalHeader()
    header.resizeSection(1, 123)
    window_state.save_header(header, "test")
    assert settings.get_header_state("test")[0] == 4

    other = QTableWidget(0, 4)
    assert window_state.restore_header(other.horizontalHeader(), "test")
    assert other.horizontalHeader().sectionSize(1) == 123

    wider = QTableWidget(0, 5)                            # a column was added
    before = wider.horizontalHeader().saveState()
    assert not window_state.restore_header(wider.horizontalHeader(), "test")
    assert wider.horizontalHeader().saveState() == before

    settings.set_header_state("broken", 4, b"garbage")    # Qt rejects the state
    assert not window_state.restore_header(other.horizontalHeader(), "broken")
    assert other.horizontalHeader().count() == 4


def test_off_screen_geometry_falls_back(app):
    screen = QApplication.primaryScreen().availableGeometry()
    assert window_state.is_on_screen(QRect(screen.left() + 10, screen.top() + 10, 300, 200))
    assert not window_state.is_on_screen(QRect(screen.right() + 500, 0, 300, 200))
    assert not window_state.is_on_screen(QRect(0, screen.bottom() + 500, 300, 200))

    dialog = QDialog()
    dialog.resize(400, 300)
    dialog.move(screen.right() + 2000, screen.bottom() + 2000)
    window_state.save_geometry(dialog, "far_away")
    restored = QDialog()
    restored.resize(400, 300)
    window_state.restore_geometry(restored, "far_away")
    assert window_state.is_on_screen(restored.geometry())
    assert restored.size().width() == 400


def test_collection_dialog_remembers_geometry_and_sort_column(app, message_boxes):
    _add(artist="A", year="1999")
    _add(artist="B", year="1970")
    dlg = CollectionDialog()
    dlg.resize(900, 555)
    dlg._table.sortByColumn(_COL_YEAR, Qt.SortOrder.DescendingOrder)
    dlg.reject()
    assert settings.get_window_geometry("collection_dialog") is not None

    again = CollectionDialog()
    header = again._table.horizontalHeader()
    assert header.sortIndicatorSection() == _COL_YEAR
    assert header.sortIndicatorOrder() == Qt.SortOrder.DescendingOrder
    assert again._table.item(0, _COL_YEAR).text() == "1999"
    assert again.size().height() == 555


def test_review_dialog_uses_one_key_for_both_modes(app, message_boxes):
    queue = ReviewDialog([], parent=None)
    queue.resize(700, 501)
    queue.reject()
    imported = ReviewDialog([], import_mode=True)
    assert imported.size().height() == 501


def test_columns_become_resizable_after_the_first_show(app, message_boxes):
    from PyQt6.QtWidgets import QHeaderView

    _add()                                                # else the empty hint is shown
    dlg = CollectionDialog()
    header = dlg._table.horizontalHeader()
    assert header.sectionResizeMode(2) == QHeaderView.ResizeMode.Stretch
    dlg.show()
    app.processEvents()
    assert header.sectionResizeMode(2) == QHeaderView.ResizeMode.Interactive
    assert header.sectionResizeMode(0) == QHeaderView.ResizeMode.Fixed   # checkbox
    dlg.reject()


# ── 4. Keyboard shortcuts ─────────────────────────────────────────────────────

def test_main_window_shortcuts_and_tooltips(window):
    shortcuts = {
        name: [seq.toString() for seq in sc.keys()] for name, sc in window._shortcuts.items()
    }
    assert shortcuts["load_data"] == ["Ctrl+L"]
    assert shortcuts["queue"] == ["Ctrl+E"]
    assert shortcuts["create_pdf"] == ["Ctrl+Shift+P"]
    assert "Ctrl+P" in shortcuts["print"]
    assert shortcuts["settings"] == ["Ctrl+,"]
    assert window._sidebar._btn_print.toolTip() == "Print (Ctrl+P)"
    assert window._sidebar._btn_load_data.toolTip().endswith("(Ctrl+L)")

    window._shortcuts["print"].activated.emit()           # disabled: nothing happens
    assert window.calls["printed"] == []


def test_collection_dialog_shortcuts_respect_the_buttons(app, monkeypatch, message_boxes):
    record = _add()
    dlg = CollectionDialog()
    asked = []
    monkeypatch.setattr(dlg, "_confirm_delete", lambda ids: asked.append(ids) or False)
    dlg._click(dlg._btn_delete)                           # nothing selected: disabled
    assert asked == []
    dlg._select_record(record.id)
    dlg._click(dlg._btn_delete)                           # with the usual confirmation
    assert asked == [[record.id]]
    assert label_store.get_record(record.id) is not None
    assert dlg._btn_delete.toolTip() == "Delete (Del)"
    assert dlg._btn_new.toolTip() == "New record (Ctrl+N)"


def test_review_dialog_shortcuts_do_not_fire_while_editing(app, message_boxes):
    rows = [dict(title="One", artist="X", side="A"), dict(title="Two", artist="Y", side="B")]
    dlg = ReviewDialog(rows)
    dlg.show()
    dlg.activateWindow()
    table = dlg._table
    table.setFocus()
    table.selectRow(0)
    app.processEvents()

    index = table.model().index(0, 1)
    table.edit(index)
    assert is_editing(table)
    editor = table.indexWidget(index)
    assert editor is not None
    # The editor claims every key: Del deletes text, not rows
    event = QKeyEvent(QEvent.Type.ShortcutOverride, Qt.Key.Key_Delete,
                      Qt.KeyboardModifier.NoModifier)
    event.ignore()
    QApplication.sendEvent(editor, event)
    assert event.isAccepted()
    QTest.keyClick(editor, Qt.Key.Key_Delete)
    QTest.keyClick(editor, Qt.Key.Key_S, Qt.KeyboardModifier.ControlModifier)
    dlg._on_delete_shortcut()
    assert table.rowCount() == 2
    assert dlg.isVisible()                                # Ctrl+S did not save

    QTest.keyClick(editor, Qt.Key.Key_Escape)             # close the editor
    assert not is_editing(table)
    table.setFocus()
    table.selectRow(0)
    QTest.keyClick(table, Qt.Key.Key_Delete)
    assert table.rowCount() == 1
    dlg.done(QDialog.DialogCode.Rejected.value)           # skip the unsaved question


# ── 5. Footer in LOCAL mode ───────────────────────────────────────────────────

def test_collection_counts():
    assert label_store.collection_counts() == (0, 0)
    both = _add(artist="Both printed")
    half = _add(artist="Only A printed")
    _add(artist="A only, unprinted", title_b="")
    a_only = _add(artist="A only, printed", title_b="")
    label_store.mark_sides_printed([(both.id, "A"), (both.id, "B"), (half.id, "A"),
                                    (a_only.id, "A")])
    assert label_store.collection_counts() == (4, 2)
    assert sum(bool(r.unprinted_sides()) for r in label_store.list_records()) == 2


def test_footer_shows_the_collection_status_in_local_mode(window):
    footer = window._footer
    assert footer.collection_text() == "Collection empty"
    assert footer._lbl_collection.isVisibleTo(footer)
    assert not footer._dot.isVisibleTo(footer)
    assert not footer._lbl_username.isVisibleTo(footer)

    record = _add()
    label_store.append_to_queue(queue_rows_for_sides(record, "A"))
    window._load_queue()                                  # any queue change refreshes
    assert footer.collection_text() == "1 records · 1 not printed"

    window.on_create_pdf()
    window.on_print()                                     # printed marking: answered yes
    assert footer.collection_text() == "1 records · 1 not printed"   # B is still open
    label_store.mark_sides_printed([(record.id, "B")])
    window._load_queue()
    assert footer.collection_text() == "1 records · 0 not printed"

    set_language("DE")
    try:
        window._retranslate_ui()
        assert footer.collection_text() == "1 Platten · 0 nicht gedruckt"
    finally:
        set_language("EN")


def test_footer_in_discogs_mode_is_unchanged(window):
    window.on_mode_changed(DataSourceMode.DISCOGS.value)
    footer = window._footer
    assert footer._dot.isVisibleTo(footer)
    assert footer._lbl_username.isVisibleTo(footer)
    assert footer._lbl_username.text() == "Not connected"
    assert not footer._lbl_collection.isVisibleTo(footer)
    assert footer._lbl_mode.text() == "Discogs mode"


def test_collection_dialog_changes_refresh_the_footer(window, monkeypatch):
    def fake_exec(dlg):
        label_store.add_record(_record())
        dlg.reload()
        assert window._footer.collection_text() == "1 records · 1 not printed"
        return QDialog.DialogCode.Rejected

    monkeypatch.setattr(CollectionDialog, "exec", fake_exec)
    window.on_load_data()
    assert window._footer.collection_text() == "1 records · 1 not printed"


def test_mode_badge_opens_the_data_source_tab(window):
    footer = window._footer
    assert footer._lbl_mode.cursor().shape() == Qt.CursorShape.PointingHandCursor
    assert footer._lbl_mode.toolTip()
    footer._lbl_mode.clicked.emit()
    assert window._settings_dialog._stack.currentIndex() == 1


# ── 6. Preview placeholder ────────────────────────────────────────────────────

def test_placeholder_text_per_state(window):
    preview = window._preview
    assert preview.placeholder_text() == (
        "Choose records from your collection via “Load data”."
    )
    window.on_mode_changed(DataSourceMode.DISCOGS.value)
    assert preview.placeholder_text() == "Load records from Discogs via “Load data”."

    label_store.append_to_queue([_one_off("One"), _one_off("Two")])
    window._load_queue()
    assert preview.placeholder_text() == (
        "2 labels in the queue – “Create PDF” shows the preview."
    )

    set_language("DE")
    try:
        window._retranslate_ui()
        assert preview.placeholder_text() == (
            "2 Etiketten in der Warteschlange – „PDF erstellen“ zeigt die Vorschau."
        )
        label_store.replace_queue([])
        window._load_queue()
        assert preview.placeholder_text() == "Lade über „Daten laden“ Platten aus Discogs."
        window.on_mode_changed(DataSourceMode.LOCAL.value)
        assert preview.placeholder_text() == (
            "Wähle über „Daten laden“ Platten aus deiner Sammlung."
        )
    finally:
        set_language("EN")


def test_placeholder_color_follows_the_theme(window):
    from config.themes import THEMES
    from ui.theme_manager import ThemeManager

    manager = ThemeManager.instance()
    previous = manager.setting
    try:
        for name in ("light", "dark"):
            manager.set_setting(name, persist=False)
            assert THEMES[name].text_muted in window._preview._placeholder.styleSheet()
    finally:
        manager.set_setting(previous, persist=False)

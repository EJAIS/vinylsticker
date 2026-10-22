"""
Robustness fixes from the 1.2 code review: "Print" does not block the GUI,
the start position picker regenerates the PDF once, and the calibration PDF
error box names the right problem.

(The fallback font is covered in test_pdf_fonts.py, the CSV formula
protection in test_csv_io.py and test_collection_sync.py.)
"""

from __future__ import annotations

import os
import signal
import sys
import time

import pytest
from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QMessageBox, QPushButton

from config import settings
from modules import label_store, printer
from modules.i18n import set_language
from modules.records import LabelRecord
from ui.grid_widget import GridWidget


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance() or QApplication([])
    set_language("EN")
    yield application


@pytest.fixture(autouse=True)
def settings_file(tmp_path, monkeypatch):
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
    """Record static message boxes as (kind, title, text) instead of blocking."""
    shown: list[tuple[str, str, str]] = []
    for name in ("critical", "warning", "information", "question"):
        monkeypatch.setattr(
            QMessageBox, name,
            lambda *args, _name=name, **kwargs: shown.append((_name, args[1], args[2])),
        )
    return shown


@pytest.fixture
def window(app, monkeypatch, message_boxes, tmp_path):
    """A main window that records PDF generations as their start positions."""
    import ui.app as app_module

    generated: list[int] = []

    def fake_generate_pdf(records, output_path, **kwargs):
        generated.append(kwargs["start_position"])
        output_path.write_bytes(b"%PDF-1.4\n")
        return output_path

    output = tmp_path / "output"
    output.mkdir()
    monkeypatch.setattr(app_module, "generate_pdf", fake_generate_pdf)
    monkeypatch.setattr(app_module.PreviewWidget, "load_pdf", lambda preview, path: None)
    monkeypatch.setattr(app_module, "get_output_dir", lambda: output)
    win = app_module.MainWindow()
    win.generated = generated
    return win


# ── 1. Print does not block the GUI ───────────────────────────────────────────

_FAKE_XDG_OPEN = """#!/bin/sh
# Stands for a viewer that stays open: reports its pid and standard streams,
# then waits.
streams=$(readlink /proc/$$/fd/0 /proc/$$/fd/1 /proc/$$/fd/2)
printf '%s\n%s\n' "$$" "$streams" > "{report}.tmp"
mv "{report}.tmp" "{report}"
sleep 30
"""


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="xdg-open is Linux only")
def test_print_on_linux_returns_while_the_viewer_is_open(tmp_path, monkeypatch):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    report = tmp_path / "report.txt"
    script = bin_dir / "xdg-open"
    script.write_text(_FAKE_XDG_OPEN.format(report=report))
    script.chmod(0o755)
    pdf = tmp_path / "labels.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setattr(printer, "get_show_print_hint", lambda: False)

    started = time.monotonic()
    printer.print_pdf(pdf)
    assert time.monotonic() - started < 1.0

    deadline = time.monotonic() + 10
    while not report.exists() and time.monotonic() < deadline:
        time.sleep(0.05)
    lines = report.read_text().split()
    pid = int(lines[0])
    try:
        # No pipes to the app and a session of its own
        assert lines[1:4] == ["/dev/null"] * 3
        assert os.getsid(pid) == pid
        assert os.getsid(0) != pid
    finally:
        os.killpg(pid, signal.SIGTERM)


def test_print_without_xdg_open_raises_runtime_error(tmp_path, monkeypatch):
    pdf = tmp_path / "labels.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    monkeypatch.setattr(printer, "get_show_print_hint", lambda: False)
    monkeypatch.setattr(printer.sys, "platform", "linux")
    with pytest.raises(RuntimeError, match="xdg-open not found"):
        printer.print_pdf(pdf)


def test_print_on_macos_does_not_wait(tmp_path, monkeypatch):
    started: list[tuple[list[str], dict]] = []

    class FakePopen:
        def __init__(self, command, **kwargs):
            started.append((command, kwargs))

        def wait(self, *args, **kwargs):
            raise AssertionError("must not wait for the viewer")

        communicate = wait

    pdf = tmp_path / "labels.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    monkeypatch.setattr(printer.subprocess, "Popen", FakePopen)
    monkeypatch.setattr(printer, "get_show_print_hint", lambda: False)
    monkeypatch.setattr(printer.sys, "platform", "darwin")
    printer.print_pdf(pdf)
    command, kwargs = started[0]
    assert command == ["open", "-a", "Preview", str(pdf.resolve())]
    assert kwargs["start_new_session"] is True
    for stream in ("stdin", "stdout", "stderr"):
        assert kwargs[stream] == printer.subprocess.DEVNULL


# ── 4. Start position picker regenerates once ─────────────────────────────────

def _click(grid: GridWidget, index: int) -> None:
    rect = grid._cell_rect(index % GridWidget.COLS, index // GridWidget.COLS)
    QTest.mouseClick(grid, Qt.MouseButton.LeftButton, pos=rect.center())


def _with_pdf(window) -> None:
    label_store.append_to_queue([LabelRecord("One", "X", "", "", "", "A")])
    window._load_queue()
    window.on_create_pdf()
    window.generated.clear()


def test_three_clicks_and_ok_regenerate_once(window):
    _with_pdf(window)
    dlg = window._create_start_pos_dialog()
    grid = dlg.findChild(GridWidget)
    for index in (3, 9, 5):
        _click(grid, index)
    assert window.generated == []                         # clicks only move the marker
    assert window._start_index == 5
    dlg.findChild(QPushButton).click()                    # OK
    assert window.generated == [5]


def test_ok_without_a_change_does_not_regenerate(window):
    _with_pdf(window)
    dlg = window._create_start_pos_dialog()
    dlg.findChild(QPushButton).click()
    assert window.generated == []


def test_clicking_back_to_the_old_position_does_not_regenerate(window):
    _with_pdf(window)
    dlg = window._create_start_pos_dialog()
    grid = dlg.findChild(GridWidget)
    _click(grid, 4)
    _click(grid, 0)
    dlg.findChild(QPushButton).click()
    assert window.generated == []


def test_close_button_regenerates_once(window):
    _with_pdf(window)
    dlg = window._create_start_pos_dialog()
    dlg.show()
    _click(dlg.findChild(GridWidget), 7)
    _click(dlg.findChild(GridWidget), 8)
    dlg.close()                                           # window close button
    assert window.generated == [8]
    assert window._start_index == 8


def test_no_pdf_in_session_no_generation(window):
    label_store.append_to_queue([LabelRecord("One", "X", "", "", "", "A")])
    window._load_queue()
    dlg = window._create_start_pos_dialog()
    _click(dlg.findChild(GridWidget), 6)
    dlg.findChild(QPushButton).click()
    assert window.generated == []
    assert window._start_index == 6


# ── 5. Calibration PDF error box ──────────────────────────────────────────────

@pytest.mark.parametrize("language, text", [
    ("EN", "The calibration PDF could not be created:\ndisk full"),
    ("DE", "Die Kalibrierungs-PDF konnte nicht erstellt werden:\ndisk full"),
])
def test_calibration_pdf_error_box(app, monkeypatch, message_boxes, language, text):
    from modules import pdf_generator
    from modules.i18n import t
    from ui.settings_dialog import SettingsDialog

    def failing(output_path, fmt):
        raise OSError("disk full")

    monkeypatch.setattr(pdf_generator, "generate_calibration_pdf", failing)
    set_language(language)
    try:
        dialog = SettingsDialog()
        dialog._on_generate_calibration_pdf()
        assert message_boxes == [("critical", t("app_title"), text)]
    finally:
        set_language("EN")

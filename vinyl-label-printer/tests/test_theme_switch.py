"""
Regression test: a theme switch restyles every open window and dialog at once.

Opens the main window, the settings dialog, the review dialog, the start
position dialog and the Discogs dialog, switches dark -> light -> dark and
checks after each switch that no widget still carries a color of the theme
that is no longer active.
"""

from __future__ import annotations

import re
from dataclasses import astuple
from pathlib import Path

import pytest
from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QApplication, QLabel, QMessageBox

import ui.theme_manager as theme_manager
from config.settings import get_theme as get_saved_theme
from config.stylesheet import build_stylesheet
from config.themes import THEMES, ThemeColors
from modules.i18n import set_language
from modules.paths import seed_example_database
from ui.app import MainWindow
from ui.discogs_dialog import DiscogsDialog
from ui.review_widget import ReviewDialog
from ui.theme_manager import ThemeManager, resolve_auto_theme

_HEX_COLOR = re.compile(r"#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")

# Row 0 complete, row 1 without title, row 2 without side
_RECORDS = [
    dict(title="Song A", artist="X", label="L", catno="1", country="DE",
         year="1970", side="A"),
    dict(title="", artist="Y", label="L", catno="2", country="UK",
         year="1971", side="B"),
    dict(title="Song C", artist="Z", label="", catno="", country="", year="",
         side=""),
]


def _normalise(color: str) -> str:
    """#abc / #AABBCC -> #aabbcc"""
    color = color.lower()
    if len(color) == 4:
        color = "#" + "".join(ch * 2 for ch in color[1:])
    return color


def _theme_hexes(colors: ThemeColors) -> set[str]:
    return {_normalise(value) for value in astuple(colors)}


def _inactive_only(active: str) -> set[str]:
    """Colors that exist only in the theme that is not *active*."""
    inactive = "light" if active == "dark" else "dark"
    return _theme_hexes(THEMES[inactive]) - _theme_hexes(THEMES[active])


def _flush_deletes(app: QApplication) -> None:
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete.value)
    app.processEvents()


def _stale_colors(app: QApplication, active: str) -> list[str]:
    """Widgets whose own stylesheet (or rich text) uses an inactive-only color."""
    stale = _inactive_only(active)
    found = []
    for widget in app.allWidgets():
        sources = [widget.styleSheet()]
        if isinstance(widget, QLabel):
            sources.append(widget.text())   # e.g. link colors in rich text
        for source in sources:
            for match in _HEX_COLOR.findall(source):
                if _normalise(match) in stale:
                    found.append(
                        f"{type(widget).__name__}({widget.objectName()!r}): {match}"
                    )
    return found


def _assert_theme(app: QApplication, settings_dialog, review: ReviewDialog,
                  setting: str, resolved: str) -> None:
    manager = ThemeManager.instance()
    colors = THEMES[resolved]
    assert manager.setting == setting
    assert manager.resolved == resolved
    assert manager.colors == colors
    assert app.styleSheet() == build_stylesheet(colors)
    assert app.property("theme_colors") == colors
    assert get_saved_theme() == setting

    assert _stale_colors(app, resolved) == []

    # The active theme card always matches the saved setting
    for name, card in settings_dialog._theme_cards.items():
        assert card._active == (name == setting), name

    # Per-cell backgrounds of the review table follow the theme
    table = review._table
    title_missing = table.item(1, 1)
    side_missing = table.item(2, 7)
    row_tinted = table.item(2, 2)
    complete = table.item(0, 1)
    assert title_missing.background().color() == QColor(colors.cell_error_bg)
    assert side_missing.background().color() == QColor(colors.cell_error_bg)
    assert row_tinted.background().color() == QColor(colors.row_warn_bg)
    assert complete.background().style() == Qt.BrushStyle.NoBrush

    # ... and are actually painted (not hidden by the global item stylesheet)
    if review.isVisible():
        table.clearSelection()
        image = table.viewport().grab().toImage()
        rect = table.visualItemRect(title_missing)
        painted = QColor(image.pixel(rect.right() - 2, rect.center().y()))
        assert painted == QColor(colors.cell_error_bg)


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance() or QApplication([])
    set_language("EN")
    ThemeManager.instance().set_setting("dark")
    yield application
    for widget in application.topLevelWidgets():
        widget.close()
        widget.deleteLater()
    _flush_deletes(application)


@pytest.fixture
def no_message_boxes(monkeypatch):
    """Fail instead of blocking on a modal message box."""
    def _fail(*args, **kwargs):
        raise AssertionError(f"unexpected message box: {args[1:3]}")
    for name in ("critical", "warning", "information", "question"):
        monkeypatch.setattr(QMessageBox, name, _fail)


def test_switch_restyles_all_open_windows(app, no_message_boxes, tmp_path: Path):
    seed_example_database()
    manager = ThemeManager.instance()
    manager.set_setting("dark")

    window = MainWindow()
    window.show()
    window.on_open_settings()
    settings_dialog = window._settings_dialog
    review = ReviewDialog(_RECORDS, tmp_path / "database.xlsx", parent=window)
    review.show()
    start_pos = window._create_start_pos_dialog()
    start_pos.show()
    app.processEvents()

    _assert_theme(app, settings_dialog, review, "dark", "dark")

    manager.set_setting("light")
    # Opened after the switch: must start with the current colors
    discogs = DiscogsDialog(tmp_path / "database.xlsx", parent=window)
    discogs.show()
    app.processEvents()
    _assert_theme(app, settings_dialog, review, "light", "light")

    manager.set_setting("dark")
    app.processEvents()
    _assert_theme(app, settings_dialog, review, "dark", "dark")

    # A closed and deleted dialog no longer receives theme_changed
    discogs.close()
    discogs.deleteLater()
    _flush_deletes(app)
    manager.set_setting("light")
    app.processEvents()
    _assert_theme(app, settings_dialog, review, "light", "light")

    # Clicking a theme card saves and applies the setting
    settings_dialog._theme_cards["dark"].clicked.emit()
    app.processEvents()
    _assert_theme(app, settings_dialog, review, "dark", "dark")

    for dialog in (start_pos, review, settings_dialog, window):
        dialog.close()
        dialog.deleteLater()
    _flush_deletes(app)


def test_auto_follows_system_theme(app, no_message_boxes, monkeypatch, tmp_path: Path):
    manager = ThemeManager.instance()
    manager.set_setting("light")
    window = MainWindow()
    window.on_open_settings()
    settings_dialog = window._settings_dialog
    review = ReviewDialog(_RECORDS, tmp_path / "database.xlsx", parent=window)

    system = {"theme": "dark"}
    monkeypatch.setattr(
        theme_manager, "resolve_auto_theme",
        lambda scheme, window_color: (system["theme"], "test"),
    )

    manager.set_setting("auto")
    _assert_theme(app, settings_dialog, review, "auto", "dark")

    # OS switches to light while the setting is "auto" -> follow live
    system["theme"] = "light"
    manager._on_system_theme_changed()
    _assert_theme(app, settings_dialog, review, "auto", "light")

    # A fixed setting ignores OS switches
    manager.set_setting("dark")
    system["theme"] = "light"
    manager._on_system_theme_changed()
    _assert_theme(app, settings_dialog, review, "dark", "dark")

    for dialog in (review, settings_dialog, window):
        dialog.close()
        dialog.deleteLater()
    _flush_deletes(app)


@pytest.mark.parametrize(
    ("scheme", "window_color", "expected"),
    [
        (Qt.ColorScheme.Dark, "#ffffff", "dark"),
        (Qt.ColorScheme.Light, "#000000", "light"),
        (Qt.ColorScheme.Unknown, "#2b2b2b", "dark"),   # e.g. Cinnamon without portal
        (Qt.ColorScheme.Unknown, "#efefef", "light"),
    ],
)
def test_resolve_auto_theme(scheme, window_color, expected):
    theme, reason = resolve_auto_theme(scheme, QColor(window_color))
    assert theme == expected
    assert reason


def test_theme_colors_are_hex():
    for colors in THEMES.values():
        for value in astuple(colors):
            assert _HEX_COLOR.fullmatch(value), value

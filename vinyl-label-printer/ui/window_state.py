"""
Remembered window geometry and table header state (settings.json).

Windows call restore_geometry() / HeaderKeeper.restore() at the end
of their construction, after the default size and the header setup are in
place, and save_geometry() / HeaderKeeper.save() when they close (QDialog.done(),
QMainWindow.closeEvent()). The Qt blobs are stored by config.settings.

Columns: the dialogs lay out their tables with Stretch / ResizeToContents
sections, which the user cannot resize. After the first show,
make_interactive() turns these into user-resizable sections with the widths
of that layout (sections restored from a stored state already are); the
stored state then holds the user's widths and sort column.

A restored geometry that is no longer reachable (e.g. the monitor it was on
was removed) falls back to the default size, centered on the parent. A stored
header state is ignored if the table's column count changed or Qt rejects it.
"""

from __future__ import annotations

from PyQt6 import sip
from PyQt6.QtCore import QByteArray, QEvent, QObject, QPoint, QRect, QSize, QTimer
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QHeaderView, QWidget

from config.settings import (
    get_header_state,
    get_window_geometry,
    set_header_state,
    set_window_geometry,
)
from modules.logger import get_logger

logger = get_logger()

# Part of the window's top edge (title bar) that must lie on a screen, in px
_MIN_VISIBLE_WIDTH = 80
_TITLE_BAR_HEIGHT = 24


def is_on_screen(rect: QRect) -> bool:
    """Whether the top edge of *rect* (where the title bar is) is on any screen."""
    title_bar = QRect(rect.left(), rect.top(), rect.width(), _TITLE_BAR_HEIGHT)
    for screen in QGuiApplication.screens():
        visible = title_bar.intersected(screen.availableGeometry())
        if visible.width() >= min(_MIN_VISIBLE_WIDTH, rect.width()) and visible.height() > 0:
            return True
    return False


def center_on_parent(widget: QWidget, size: QSize) -> None:
    """Resize *widget* to *size* and center it on its parent (or the primary screen)."""
    widget.resize(size)
    parent = widget.parentWidget()
    if parent is not None and parent.isVisible():
        area = parent.window().frameGeometry()
    else:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
    widget.move(area.center() - QPoint(size.width() // 2, size.height() // 2))


def restore_geometry(widget: QWidget, key: str) -> bool:
    """Restore the saved geometry of *widget*; True if it was used.

    Call it after the default size was set: that size is the fallback.
    """
    default_size = widget.size().expandedTo(widget.minimumSize())
    data = get_window_geometry(key)
    if data is None:
        return False
    if not widget.restoreGeometry(QByteArray(data)):
        logger.debug(f"Stored geometry of {key} is invalid — using the default size")
        return False
    if not is_on_screen(widget.geometry()):
        logger.info(f"Stored geometry of {key} is off-screen — using the default size")
        center_on_parent(widget, default_size)
        return False
    return True


def save_geometry(widget: QWidget, key: str) -> None:
    try:
        set_window_geometry(key, bytes(widget.saveGeometry()))
    except OSError as exc:
        logger.warning(f"Could not save the geometry of {key}: {exc}")


def restore_header(header: QHeaderView, key: str) -> bool:
    """Restore the saved state (column widths, order, sort column) of *header*.

    The stored state is ignored when the column count differs or Qt rejects it;
    then the header keeps the state it had before the call.
    """
    stored = get_header_state(key)
    if stored is None:
        return False
    columns, data = stored
    count = header.count()
    if columns != count:
        logger.debug(f"Stored header of {key} has {columns} columns, table {count} — ignored")
        return False
    before = header.saveState()
    if not header.restoreState(QByteArray(data)) or header.count() != count:
        logger.debug(f"Stored header state of {key} is invalid — ignored")
        header.restoreState(before)
        return False
    return True


def save_header(header: QHeaderView, key: str) -> None:
    try:
        set_header_state(key, header.count(), bytes(header.saveState()))
    except OSError as exc:
        logger.warning(f"Could not save the table columns of {key}: {exc}")


def make_interactive(header: QHeaderView) -> None:
    """Freeze Stretch / ResizeToContents sections at their current width as resizable ones.

    Fixed sections (e.g. checkbox columns) stay fixed; the last section
    stretches to fill the table.
    """
    automatic = (QHeaderView.ResizeMode.Stretch, QHeaderView.ResizeMode.ResizeToContents)
    for section in range(header.count()):
        if header.sectionResizeMode(section) in automatic:
            width = header.sectionSize(section)
            header.setSectionResizeMode(section, QHeaderView.ResizeMode.Interactive)
            header.resizeSection(section, width)
    header.setStretchLastSection(True)


class HeaderKeeper(QObject):
    """Restores, freezes (see make_interactive) and saves the header of one table.

    restore() at the end of the dialog's construction, save() from its
    done(). The freeze runs once the header is first shown (the table may sit
    on a page of a stacked widget that is shown later).
    """

    def __init__(self, header: QHeaderView, key: str) -> None:
        super().__init__(header)
        self._header = header
        self._key = key
        self._shown = False
        self._frozen = False
        header.installEventFilter(self)

    def restore(self) -> bool:
        return restore_header(self._header, self._key)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802
        if obj is self._header and event.type() == QEvent.Type.Show and not self._shown:
            self._shown = True
            # After the layout pass, so the automatic widths are the final ones
            QTimer.singleShot(0, self._freeze)
        return False

    def _freeze(self) -> None:
        if not self._frozen and not sip.isdeleted(self._header):
            self._frozen = True
            make_interactive(self._header)

    def save(self) -> None:
        if self._shown:
            # Closed before the deferred freeze ran: store resizable sections
            self._freeze()
        save_header(self._header, self._key)

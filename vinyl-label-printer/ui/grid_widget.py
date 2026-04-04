"""
Grid widget — interactive 4×10 label-sheet picker.

The widget renders a miniature representation of an Avery 4780 sheet.
The user clicks a cell to choose the first label slot to use.  Cells before
the chosen start index are shown in a darker grey ("skipped"); cells that
will receive a printed label are shown in green ("active"); remaining cells
are light grey ("empty").
"""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal, QRect, Qt
from PyQt6.QtGui import QPainter, QColor, QMouseEvent, QPen
from PyQt6.QtWidgets import QWidget


class GridWidget(QWidget):
    """4×10 clickable grid representing one Avery 4780 label sheet."""

    # Emits the 0-based linear index (row-major) of the chosen start cell.
    startPositionChanged = pyqtSignal(int)

    # Sheet geometry
    COLS = 4
    ROWS = 10
    LABELS_PER_SHEET = COLS * ROWS  # 40

    # Cell pixel dimensions
    CELL_W   = 40
    CELL_H   = 22
    PADDING  =  2   # gap between cells

    # Colours
    COLOR_EMPTY   = QColor(235, 235, 235)   # unfilled slot
    COLOR_SKIPPED = QColor(160, 160, 160)   # before start_index
    COLOR_ACTIVE  = QColor(144, 238, 144)   # will be printed
    COLOR_BORDER  = QColor( 90,  90,  90)   # cell outline
    COLOR_HOVER   = QColor(200, 230, 255)   # mouse-over highlight

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._start_index:    int = 0
        self._total_records:  int = 0
        self._hovered_index:  int | None = None

        total_w = self.COLS * (self.CELL_W + self.PADDING) + self.PADDING
        total_h = self.ROWS * (self.CELL_H + self.PADDING) + self.PADDING
        self.setFixedSize(total_w, total_h)
        self.setMouseTracking(True)

    # ── Public setters ────────────────────────────────────────────────────────

    def set_total_records(self, n: int) -> None:
        """Update how many labels will be printed; triggers a repaint."""
        self._total_records = max(0, n)
        self.update()

    def set_start_index(self, index: int) -> None:
        """Programmatically set the start cell; triggers a repaint."""
        self._start_index = max(0, min(index, self.LABELS_PER_SHEET - 1))
        self.update()

    @property
    def start_index(self) -> int:
        return self._start_index

    # ── Qt event overrides ────────────────────────────────────────────────────

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        pen = QPen(self.COLOR_BORDER)
        pen.setWidth(1)
        painter.setPen(pen)

        for row in range(self.ROWS):
            for col in range(self.COLS):
                linear = row * self.COLS + col
                rect   = self._cell_rect(col, row)
                color  = self._cell_color(linear)
                painter.fillRect(rect, color)
                painter.drawRect(rect)

                # Draw column/row label inside cell for orientation
                if linear == self._start_index:
                    painter.save()
                    painter.setPen(QPen(QColor(0, 100, 0)))
                    painter.drawText(
                        rect,
                        Qt.AlignmentFlag.AlignCenter,
                        str(linear + 1),
                    )
                    painter.restore()

        painter.end()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            index = self._index_at(int(event.position().x()),
                                   int(event.position().y()))
            if index is not None and index != self._start_index:
                self._start_index = index
                self.update()
                self.startPositionChanged.emit(self._start_index)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        index = self._index_at(int(event.position().x()),
                               int(event.position().y()))
        if index != self._hovered_index:
            self._hovered_index = index
            self.update()

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hovered_index = None
        self.update()

    # ── Private helpers ───────────────────────────────────────────────────────

    def _cell_rect(self, col: int, row: int) -> QRect:
        x = self.PADDING + col * (self.CELL_W + self.PADDING)
        y = self.PADDING + row * (self.CELL_H + self.PADDING)
        return QRect(x, y, self.CELL_W, self.CELL_H)

    def _index_at(self, px: int, py: int) -> int | None:
        """Return the linear cell index under pixel position (px, py), or None."""
        for row in range(self.ROWS):
            for col in range(self.COLS):
                if self._cell_rect(col, row).contains(px, py):
                    return row * self.COLS + col
        return None

    def _cell_color(self, linear_index: int) -> QColor:
        if linear_index == self._hovered_index:
            return self.COLOR_HOVER
        if linear_index < self._start_index:
            return self.COLOR_SKIPPED
        if linear_index < self._start_index + self._total_records:
            return self.COLOR_ACTIVE
        return self.COLOR_EMPTY

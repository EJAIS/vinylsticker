"""
ReviewDialog — editable preview of expanded tracklist rows before they are
written to the Excel Print sheet.

The user can:
  • Edit any cell directly (double-click, F2, or just start typing)
  • Re-order rows via drag & drop
  • Delete / duplicate rows via context menu or toolbar
  • Add blank rows for manual entries
  • Filter visible rows with a live search bar
  • Check / uncheck individual rows — only checked rows are written

Visual cues:
  • Empty required field (Title / Side) → cell red (#FFEBEE) + tooltip
  • Row with any empty required field  → all cells lightly tinted (#FFF5F5)
  • Cell just edited → brief yellow flash (#FFF9C4, 600 ms), then returns
    to the appropriate state (red if still empty, else clear)
  • No persistent "edited" colour — only the error tint is permanent
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from modules.excel_reader import LabelRecord, write_print_queue
from modules.i18n import t
from ui.styles import apply_search_style, apply_table_style

# ── Column indices ────────────────────────────────────────────────────────────

_COL_CHECK   = 0
_COL_TITLE   = 1
_COL_ARTIST  = 2
_COL_LABEL   = 3
_COL_COUNTRY = 4
_COL_YEAR    = 5
_COL_SIDE    = 6
_NUM_COLS    = 7

_EDITABLE_COLS = (_COL_TITLE, _COL_ARTIST, _COL_LABEL, _COL_COUNTRY, _COL_YEAR, _COL_SIDE)
_REQUIRED_COLS = (_COL_TITLE, _COL_SIDE)

# ── Colours ───────────────────────────────────────────────────────────────────

_COLOR_CELL_ERROR  = QColor("#FFEBEE")   # empty required field
_COLOR_ROW_WARN    = QColor("#FFF5F5")   # row contains an empty required field
_COLOR_BLINK       = QColor("#FFF9C4")   # transient blink on edit (600 ms)

# ── StyleSheets ───────────────────────────────────────────────────────────────

_CONFIRM_BUTTON_STYLESHEET = """
QPushButton {
    background-color: #1976D2;
    color: white;
    padding: 6px 18px;
    border-radius: 4px;
    font-weight: bold;
}
QPushButton:hover   { background-color: #1565C0; }
QPushButton:pressed { background-color: #0D47A1; }
QPushButton:disabled {
    background-color: #90CAF9;
    color: #E3F2FD;
}
"""


class ReviewDialog(QDialog):
    """Editable table of expanded tracklist rows; writes confirmed rows to Excel."""

    def __init__(
        self,
        records: list[dict],
        db_path: Path,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._db_path   = db_path
        self._populating = False
        self._confirmed_records: list[LabelRecord] = []
        self._row_count = len(records)   # total rows at open (for title)

        self.setWindowTitle(t("review_title", n=self._row_count))
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowMinimizeButtonHint
        )
        self.setMinimumSize(640, 480)
        self.resize(960, 640)
        self.setSizeGripEnabled(True)

        self._build_ui()
        self._fill_table(records)

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(6)
        root.setContentsMargins(8, 8, 8, 8)

        # ── Info banner ───────────────────────────────────────────────────────
        banner = QWidget()
        banner.setStyleSheet("""
            QWidget {
                background-color: #E8F4FD;
                border-left: 4px solid #2196F3;
                border-top: none;
                border-right: none;
                border-bottom: none;
                padding: 0px;
                margin: 0px;
            }
        """)
        banner_layout = QHBoxLayout(banner)
        banner_layout.setContentsMargins(12, 8, 12, 8)
        banner_layout.setSpacing(10)

        icon_lbl = QLabel("ℹ")
        icon_lbl.setStyleSheet(
            "color: #2196F3; font-size: 16px; font-weight: bold;"
            " background: transparent; border: none;"
        )
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignTop)

        text_lbl = QLabel(
            f"<b>{t('review_banner_line1')}</b><br>"
            f"<span style='color:#555;'>{t('review_banner_line2')}</span>"
        )
        text_lbl.setStyleSheet("background: transparent; border: none;")
        text_lbl.setWordWrap(True)

        banner_layout.addWidget(icon_lbl, 0, Qt.AlignmentFlag.AlignTop)
        banner_layout.addWidget(text_lbl, 1)
        root.addWidget(banner)

        # ── Toolbar ───────────────────────────────────────────────────────────
        toolbar = QHBoxLayout()
        toolbar.setSpacing(4)

        btn_all = QPushButton(t("review_btn_all"))
        btn_all.clicked.connect(lambda: self._set_all_checked(True))
        btn_none = QPushButton(t("review_btn_none"))
        btn_none.clicked.connect(lambda: self._set_all_checked(False))
        btn_del = QPushButton(t("review_btn_delete_sel"))
        btn_del.clicked.connect(self._delete_selected_rows)
        btn_add = QPushButton(t("review_btn_add_row"))
        btn_add.clicked.connect(self._add_empty_row)

        self._search = QLineEdit()
        self._search.setPlaceholderText(t("review_search_ph"))
        apply_search_style(self._search)
        self._search.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self._search.textChanged.connect(self._on_search)

        for w in (btn_all, btn_none, btn_del, btn_add):
            toolbar.addWidget(w)
        toolbar.addStretch()
        toolbar.addWidget(self._search)
        root.addLayout(toolbar)

        # ── Table ─────────────────────────────────────────────────────────────
        self._table = QTableWidget(0, _NUM_COLS)
        apply_table_style(self._table)

        edit_tip = t("review_col_edit_tip")
        self._table.setHorizontalHeaderLabels([
            "",                     # checkbox column — no label
            t("review_col_title"),
            t("review_col_artist"),
            t("review_col_label"),
            t("review_col_country"),
            t("review_col_year"),
            t("review_col_side"),
        ])
        hdr = self._table.horizontalHeader()
        for col in range(1, _NUM_COLS):
            hdr_item = self._table.horizontalHeaderItem(col)
            if hdr_item:
                hdr_item.setToolTip(edit_tip)

        hdr.setSectionResizeMode(_COL_CHECK, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(_COL_CHECK, 32)
        hdr.setSectionResizeMode(_COL_TITLE,   QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(_COL_ARTIST,  QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(_COL_LABEL,   QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(_COL_COUNTRY, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(_COL_YEAR,    QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(_COL_SIDE,    QHeaderView.ResizeMode.ResizeToContents)

        self._table.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self._table.setDragDropOverwriteMode(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
            | QAbstractItemView.EditTrigger.AnyKeyPressed
        )
        self._table.verticalHeader().setVisible(False)
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._on_context_menu)
        self._table.itemChanged.connect(self._on_item_changed)

        root.addWidget(self._table)

        # ── Status bar (two lines) ────────────────────────────────────────────
        self._lbl_status_counts  = QLabel("")
        self._lbl_status_warning = QLabel("")
        root.addWidget(self._lbl_status_counts)
        root.addWidget(self._lbl_status_warning)

        # ── Bottom buttons ────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_cancel = QPushButton(t("review_btn_cancel"))
        btn_cancel.clicked.connect(self.reject)

        self._btn_confirm = QPushButton(t("review_btn_confirm"))
        self._btn_confirm.setDefault(True)
        self._btn_confirm.setEnabled(False)   # enabled once rows are checked
        self._btn_confirm.setToolTip(t("review_btn_confirm_tip"))
        self._btn_confirm.setStyleSheet(_CONFIRM_BUTTON_STYLESHEET)
        self._btn_confirm.clicked.connect(self._on_confirm)

        btn_row.addWidget(btn_cancel)
        btn_row.addStretch()
        btn_row.addWidget(self._btn_confirm)
        root.addLayout(btn_row)

    # ── Table population ──────────────────────────────────────────────────────

    def _fill_table(self, records: list[dict]) -> None:
        self._populating = True
        self._table.setRowCount(0)

        for rec in records:
            row = self._table.rowCount()
            self._table.insertRow(row)
            self._set_row(row, rec, checked=True)

        self._populating = False
        self._update_status()
        self._update_title()

    def _set_row(self, row: int, rec: dict, checked: bool = True) -> None:
        """Write one data dict into *row*."""
        chk = QTableWidgetItem()
        chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
        chk.setCheckState(
            Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        )
        self._table.setItem(row, _COL_CHECK, chk)

        values = [
            str(rec.get("title",   "") or ""),
            str(rec.get("artist",  "") or ""),
            str(rec.get("label",   "") or ""),
            str(rec.get("country", "") or ""),
            str(rec.get("year",    "") or ""),
            str(rec.get("side",    "") or ""),
        ]
        for col_offset, val in enumerate(values):
            col  = col_offset + 1
            item = QTableWidgetItem(val)
            self._table.setItem(row, col, item)

        self._refresh_cell_colors(row)

    # ── Colour helpers ────────────────────────────────────────────────────────

    def _refresh_cell_colors(self, row: int) -> None:
        """Apply (or clear) background colours on every cell in *row*."""
        # Guard: setBackground/setData fire itemChanged synchronously; without
        # this flag _on_item_changed would call _blink_cell again → recursion.
        self._populating = True
        try:
            # Determine whether this row needs overall attention tinting
            row_needs_attention = any(
                not (self._table.item(row, col) and self._table.item(row, col).text().strip())
                for col in _REQUIRED_COLS
            )

            # Checkbox cell
            chk = self._table.item(row, _COL_CHECK)
            if chk:
                if row_needs_attention:
                    chk.setBackground(QBrush(_COLOR_ROW_WARN))
                else:
                    chk.setData(Qt.ItemDataRole.BackgroundRole, None)

            # Data cells
            required_tip = t("review_cell_required_tip")
            for col in range(1, _NUM_COLS):
                item = self._table.item(row, col)
                if item is None:
                    continue
                is_required = col in _REQUIRED_COLS
                is_empty    = not item.text().strip()

                if is_required and is_empty:
                    item.setBackground(QBrush(_COLOR_CELL_ERROR))
                    item.setToolTip(required_tip)
                elif row_needs_attention:
                    item.setBackground(QBrush(_COLOR_ROW_WARN))
                    item.setToolTip("")
                else:
                    item.setData(Qt.ItemDataRole.BackgroundRole, None)
                    item.setToolTip("")
        finally:
            self._populating = False

    def _blink_cell(self, row: int, col: int) -> None:
        """Flash the cell yellow for 600 ms, then restore the correct colour."""
        item = self._table.item(row, col)
        if item:
            # Guard: setBackground fires itemChanged synchronously; set
            # _populating to prevent _on_item_changed from re-entering here.
            self._populating = True
            item.setBackground(QBrush(_COLOR_BLINK))
            self._populating = False

        # Parented timer: destroyed with the dialog, so the callback can never
        # fire after the dialog is closed (prevents use-after-free on the table).
        t = QTimer(self)
        t.setSingleShot(True)
        t.timeout.connect(lambda: self._refresh_cell_colors(row))
        t.start(600)

    # ── itemChanged slot ──────────────────────────────────────────────────────

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._populating:
            return
        row = item.row()
        col = item.column()
        if col != _COL_CHECK:
            self._blink_cell(row, col)
        else:
            # Checkbox toggled — just refresh status, no blink needed
            pass
        self._update_status()
        self._update_title()

    # ── Context menu ──────────────────────────────────────────────────────────

    def _on_context_menu(self, pos) -> None:
        row = self._table.rowAt(pos.y())
        if row < 0:
            return
        menu    = QMenu(self)
        act_del = menu.addAction(t("review_ctx_delete"))
        act_dup = menu.addAction(t("review_ctx_duplicate"))
        chosen  = menu.exec(self._table.viewport().mapToGlobal(pos))
        if chosen == act_del:
            self._delete_rows([row])
        elif chosen == act_dup:
            self._duplicate_row(row)

    # ── Toolbar slots ─────────────────────────────────────────────────────────

    def _set_all_checked(self, checked: bool) -> None:
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        self._populating = True
        for row in range(self._table.rowCount()):
            item = self._table.item(row, _COL_CHECK)
            if item:
                item.setCheckState(state)
        self._populating = False
        self._update_status()
        self._update_title()

    def _delete_selected_rows(self) -> None:
        rows = sorted(
            {idx.row() for idx in self._table.selectedIndexes()},
            reverse=True,
        )
        self._delete_rows(rows)

    def _delete_rows(self, rows: list[int]) -> None:
        for row in sorted(rows, reverse=True):
            self._table.removeRow(row)
        self._update_status()
        self._update_title()

    def _duplicate_row(self, row: int) -> None:
        rec = self._read_row(row)
        insert_at = row + 1
        self._populating = True
        self._table.insertRow(insert_at)
        self._set_row(insert_at, rec, checked=True)
        self._populating = False
        self._update_status()
        self._update_title()

    def _add_empty_row(self) -> None:
        row = self._table.rowCount()
        self._populating = True
        self._table.insertRow(row)
        self._set_row(row, {}, checked=True)
        self._populating = False
        self._update_status()
        self._update_title()

    # ── Search / filter ───────────────────────────────────────────────────────

    def _on_search(self, text: str) -> None:
        q = text.strip().lower()
        for row in range(self._table.rowCount()):
            if not q:
                self._table.setRowHidden(row, False)
                continue
            title  = (self._table.item(row, _COL_TITLE)  or QTableWidgetItem("")).text().lower()
            artist = (self._table.item(row, _COL_ARTIST) or QTableWidgetItem("")).text().lower()
            self._table.setRowHidden(row, q not in title and q not in artist)
        self._update_status()

    # ── Status bar ────────────────────────────────────────────────────────────

    def _update_status(self) -> None:
        total      = 0
        checked    = 0
        incomplete = 0

        for row in range(self._table.rowCount()):
            if self._table.isRowHidden(row):
                continue
            total += 1

            chk = self._table.item(row, _COL_CHECK)
            if chk and chk.checkState() == Qt.CheckState.Checked:
                checked += 1

            if any(
                not (self._table.item(row, col) and
                     self._table.item(row, col).text().strip())
                for col in _REQUIRED_COLS
            ):
                incomplete += 1

        self._lbl_status_counts.setText(
            t("review_status_counts", n=total, m=checked)
        )

        if incomplete:
            self._lbl_status_warning.setText(
                t("review_status_warning", k=incomplete)
            )
            self._lbl_status_warning.setStyleSheet("color: #E65100; font-weight: bold;")
        else:
            self._lbl_status_warning.setText(t("review_status_ok"))
            self._lbl_status_warning.setStyleSheet("color: #2E7D32; font-weight: bold;")

        self._btn_confirm.setEnabled(checked > 0)

    # ── Window title ──────────────────────────────────────────────────────────

    def _update_title(self) -> None:
        n = self._table.rowCount()
        incomplete = any(
            not (self._table.item(row, col) and
                 self._table.item(row, col).text().strip())
            for row in range(n)
            for col in _REQUIRED_COLS
        )
        if incomplete:
            self.setWindowTitle(t("review_title_warning", n=n))
        else:
            self.setWindowTitle(t("review_title_ok", n=n))

    # ── Confirm ───────────────────────────────────────────────────────────────

    def _on_confirm(self) -> None:
        checked_rows = [
            row for row in range(self._table.rowCount())
            if not self._table.isRowHidden(row)
            and self._table.item(row, _COL_CHECK) is not None
            and self._table.item(row, _COL_CHECK).checkState() == Qt.CheckState.Checked
        ]

        if not checked_rows:
            QMessageBox.information(self, t("review_btn_confirm"), t("review_no_sel_msg"))
            return

        invalid = [
            row for row in checked_rows
            if not (self._table.item(row, _COL_TITLE) or QTableWidgetItem("")).text().strip()
            or not (self._table.item(row, _COL_SIDE)  or QTableWidgetItem("")).text().strip()
        ]
        if invalid:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle(t("review_warn_title"))
            msg.setText(t("review_warn_msg", k=len(invalid)))
            btn_continue = msg.addButton(
                t("review_warn_continue"), QMessageBox.ButtonRole.AcceptRole
            )
            msg.addButton(t("review_warn_back"), QMessageBox.ButtonRole.RejectRole)
            msg.exec()
            if msg.clickedButton() != btn_continue:
                return

        records = [self._row_to_labelrecord(r) for r in checked_rows]

        try:
            write_print_queue(self._db_path, records)
        except Exception as exc:
            QMessageBox.critical(
                self,
                t("discogs_write_err_title"),
                t("discogs_write_err_msg", detail=str(exc)),
            )
            return

        self._confirmed_records = records
        self.accept()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _read_row(self, row: int) -> dict:
        def cell(col: int) -> str:
            item = self._table.item(row, col)
            return item.text() if item else ""

        return {
            "title":   cell(_COL_TITLE),
            "artist":  cell(_COL_ARTIST),
            "label":   cell(_COL_LABEL),
            "country": cell(_COL_COUNTRY),
            "year":    cell(_COL_YEAR),
            "side":    cell(_COL_SIDE),
        }

    def _row_to_labelrecord(self, row: int) -> LabelRecord:
        rec = self._read_row(row)
        return LabelRecord(
            title   = rec["title"],
            artist  = rec["artist"],
            label   = rec["label"],
            country = rec["country"],
            year    = rec["year"],
            side    = rec["side"],
        )

    def get_records(self) -> list[LabelRecord]:
        """Return the confirmed records after the dialog was accepted."""
        return self._confirmed_records

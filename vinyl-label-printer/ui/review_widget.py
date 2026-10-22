"""
ReviewDialog — the print queue editor, and the review of imported rows before
they are written to the print queue (labels.db, via modules.label_store).

Two modes:
  • Queue mode (default): edits the print queue itself, in LOCAL and DISCOGS
    mode. Opens also when the queue is empty; "Save" replaces the queue with
    the checked rows (nothing checked empties it, after a confirmation).
    Extra tools: "Add entry" form, CSV import and CSV export.
  • Import mode: rows come from an import (Discogs); on confirm the user
    chooses whether to append them to or replace a non-empty print queue.

The user can:
  • Edit any cell directly (double-click, F2, or just start typing)
  • Re-order rows via drag & drop
  • Delete / duplicate rows via context menu or toolbar
  • Add blank rows for manual entries
  • Filter visible rows with a live search bar
  • Check / uncheck individual rows — only checked rows are written

Nothing is written before the user confirms; closing the dialog with unsaved
changes asks whether to save, discard or keep editing.

Visual cues (colors from the active ThemeColors, refreshed on theme changes):
  • Empty required field (Title / Side) → cell red (cell_error_bg) + tooltip
  • Row with any empty required field  → all cells lightly tinted (row_warn_bg)
  • Cell just edited → brief yellow flash (blink_bg, 600 ms), then returns
    to the appropriate state (red if still empty, else clear)
  • No persistent "edited" colour — only the error tint is permanent
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from PyQt6.QtCore import QStandardPaths, Qt, QTimer
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from config.themes import ThemeColors
from modules import label_store
from modules.csv_io import CsvImportError, default_export_name, read_csv, write_csv
from modules.label_store import SOURCE_CSV, SOURCE_MANUAL
from modules.logger import get_logger
from modules.i18n import t
from modules.records import LabelRecord, normalise_side
from ui.entry_dialog import EntryDialog
from ui.styles import apply_search_style, apply_table_style
from ui.theme_manager import ThemeManager, current_colors

logger = get_logger()

# ── Column indices ────────────────────────────────────────────────────────────

_COL_CHECK   = 0
_COL_TITLE   = 1
_COL_ARTIST  = 2
_COL_LABEL   = 3
_COL_CATNO   = 4
_COL_COUNTRY = 5
_COL_YEAR    = 6
_COL_SIDE    = 7
_NUM_COLS    = 8

_EDITABLE_COLS = (
    _COL_TITLE, _COL_ARTIST, _COL_LABEL, _COL_CATNO, _COL_COUNTRY, _COL_YEAR, _COL_SIDE,
)
_REQUIRED_COLS = (_COL_TITLE, _COL_SIDE)

# Row metadata on the checkbox item (plain int / str, so drag & drop keeps it)
_ROLE_ID     = Qt.ItemDataRole.UserRole          # labels.db id, -1 for new rows
_ROLE_SOURCE = Qt.ItemDataRole.UserRole + 1      # e.g. "manual", "discogs"

# Folder of the last CSV import / export in this session
_last_csv_dir: str = ""


def _default_csv_dir() -> str:
    """Last used CSV folder, else the user's documents folder, else home."""
    if _last_csv_dir and Path(_last_csv_dir).is_dir():
        return _last_csv_dir
    documents = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.DocumentsLocation
    )
    if documents and Path(documents).is_dir():
        return documents
    return str(Path.home())


def _remember_csv_dir(path: Path) -> None:
    global _last_csv_dir
    _last_csv_dir = str(path.parent)


class _CellBackgroundDelegate(QStyledItemDelegate):
    """Paints the per-cell background colors (BackgroundRole).

    The global stylesheet styles QTableWidget::item, and with such a rule Qt
    ignores the item's own background, so the error tints would never show.
    Selection and hover colors from the stylesheet are still drawn on top.
    """

    def paint(self, painter, option, index) -> None:
        brush = index.data(Qt.ItemDataRole.BackgroundRole)
        if isinstance(brush, QBrush) and brush.style() != Qt.BrushStyle.NoBrush:
            painter.fillRect(option.rect, brush)
        super().paint(painter, option, index)


class ReviewDialog(QDialog):
    """Editable table of print queue rows; writes the checked rows to labels.db."""

    def __init__(
        self,
        records: list[dict],
        import_mode: bool = False,
        import_source: str = SOURCE_MANUAL,
        parent=None,
    ) -> None:
        """*records*: row dicts (LabelRecord fields; id / source if they come
        from labels.db). *import_mode*: rows come from an import (e.g. Discogs,
        *import_source* is their source) — ask whether to append to or replace
        a non-empty print queue on confirm. When False the dialog edits the
        queue itself and always replaces it."""
        super().__init__(parent)
        self._import_mode = import_mode
        self._import_source = import_source if import_mode else SOURCE_MANUAL
        self._populating = False
        self._saved = False
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
        # Imported rows are unsaved from the start; queue rows are what is stored
        self._saved_state = () if import_mode else self._table_state()
        self._apply_theme()
        ThemeManager.instance().theme_changed.connect(self._apply_theme)

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(6)
        root.setContentsMargins(8, 8, 8, 8)

        # ── Info banner (colors: _apply_theme) ────────────────────────────────
        self._banner = QWidget()
        banner_layout = QHBoxLayout(self._banner)
        banner_layout.setContentsMargins(12, 8, 12, 8)
        banner_layout.setSpacing(10)

        self._banner_icon = QLabel("ℹ")
        self._banner_icon.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._banner_text = QLabel()
        self._banner_text.setStyleSheet("background: transparent; border: none;")
        self._banner_text.setWordWrap(True)

        banner_layout.addWidget(self._banner_icon, 0, Qt.AlignmentFlag.AlignTop)
        banner_layout.addWidget(self._banner_text, 1)
        root.addWidget(self._banner)

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

        # ── Editor tools (queue mode only) ────────────────────────────────────
        if not self._import_mode:
            tools = QHBoxLayout()
            tools.setSpacing(4)
            btn_entry = QPushButton(t("review_btn_add_entry"))
            btn_entry.setToolTip(t("review_btn_add_entry_tip"))
            btn_entry.clicked.connect(self._on_add_entry)
            btn_import = QPushButton(t("review_btn_import_csv"))
            btn_import.setToolTip(t("review_btn_import_csv_tip"))
            btn_import.clicked.connect(self._on_import_csv)
            btn_export = QPushButton(t("review_btn_export_csv"))
            btn_export.setToolTip(t("review_btn_export_csv_tip"))
            btn_export.clicked.connect(self._on_export_csv)
            for w in (btn_entry, btn_import, btn_export):
                tools.addWidget(w)
            tools.addStretch()
            root.addLayout(tools)

        for w in (btn_all, btn_none, btn_del, btn_add):
            toolbar.addWidget(w)
        toolbar.addStretch()
        toolbar.addWidget(self._search)
        root.addLayout(toolbar)

        # ── Table ─────────────────────────────────────────────────────────────
        self._table = QTableWidget(0, _NUM_COLS)
        apply_table_style(self._table)
        self._table.setItemDelegate(_CellBackgroundDelegate(self._table))

        edit_tip = t("review_col_edit_tip")
        self._table.setHorizontalHeaderLabels([
            "",                     # checkbox column — no label
            t("review_col_title"),
            t("review_col_artist"),
            t("review_col_label"),
            t("review_col_catno"),
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
        hdr.setSectionResizeMode(_COL_CATNO,   QHeaderView.ResizeMode.ResizeToContents)
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

        if self._import_mode:
            self._btn_confirm = QPushButton(t("review_btn_confirm"))
            self._btn_confirm.setEnabled(False)   # enabled once rows are checked
            self._btn_confirm.setToolTip(t("review_btn_confirm_tip"))
        else:
            # Saving without checked rows empties the queue (after a confirmation)
            self._btn_confirm = QPushButton(t("review_btn_save"))
            self._btn_confirm.setToolTip(t("review_btn_save_tip"))
        self._btn_confirm.setDefault(True)
        self._btn_confirm.setProperty("primary", True)
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
            self._set_row(row, rec, checked=True, default_source=self._import_source)

        self._populating = False
        self._update_status()
        self._update_title()

    def _set_row(
        self,
        row: int,
        rec: dict,
        checked: bool = True,
        default_source: str = SOURCE_MANUAL,
    ) -> None:
        """Write one data dict into *row*."""
        chk = QTableWidgetItem()
        chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
        chk.setCheckState(
            Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        )
        row_id = rec.get("id")
        chk.setData(_ROLE_ID, int(row_id) if row_id is not None else -1)
        chk.setData(_ROLE_SOURCE, str(rec.get("source") or default_source))
        self._table.setItem(row, _COL_CHECK, chk)

        values = [
            str(rec.get("title",   "") or ""),
            str(rec.get("artist",  "") or ""),
            str(rec.get("label",   "") or ""),
            str(rec.get("catno",   "") or ""),
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

    def _apply_theme(self, colors: ThemeColors | None = None) -> None:
        """(Re)apply all colors; runs at build time and on theme_changed."""
        colors = colors or current_colors()
        if not colors:
            return
        self._banner.setStyleSheet(f"""
            QWidget {{
                border-left: 4px solid {colors.info_border};
                border-top: none;
                border-right: none;
                border-bottom: none;
                padding: 0px;
                margin: 0px;
            }}
        """)
        self._banner_icon.setStyleSheet(
            f"color: {colors.info_border}; font-size: 16px; font-weight: bold;"
            " background: transparent; border: none;"
        )
        # The secondary text color is part of the rich text
        prefix = "review_banner" if self._import_mode else "review_banner_queue"
        self._banner_text.setText(
            f"<b>{t(prefix + '_line1')}</b><br>"
            f"<span style='color:{colors.info_text};'>{t(prefix + '_line2')}</span>"
        )
        self._update_status()
        for row in range(self._table.rowCount()):
            self._refresh_cell_colors(row)

    def _refresh_cell_colors(self, row: int) -> None:
        """Apply (or clear) background colours on every cell in *row*."""
        colors = current_colors()
        # Without a theme the cells keep their default background
        cell_error = QBrush(QColor(colors.cell_error_bg)) if colors else QBrush()
        row_warn   = QBrush(QColor(colors.row_warn_bg)) if colors else QBrush()
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
                    chk.setBackground(row_warn)
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
                    item.setBackground(cell_error)
                    item.setToolTip(required_tip)
                elif row_needs_attention:
                    item.setBackground(row_warn)
                    item.setToolTip("")
                else:
                    item.setData(Qt.ItemDataRole.BackgroundRole, None)
                    item.setToolTip("")
        finally:
            self._populating = False

    def _blink_cell(self, row: int, col: int) -> None:
        """Flash the cell yellow for 600 ms, then restore the correct colour."""
        item = self._table.item(row, col)
        colors = current_colors()
        if item and colors:
            # Guard: setBackground fires itemChanged synchronously; set
            # _populating to prevent _on_item_changed from re-entering here.
            self._populating = True
            item.setBackground(QBrush(QColor(colors.blink_bg)))
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
            # Only affect what the user sees; rows hidden by the search filter
            # keep their current check state.
            if self._table.isRowHidden(row):
                continue
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
        rec["id"] = None   # the copy is a new queue entry
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

    def _append_records(self, records: list[LabelRecord], source: str) -> None:
        """Append *records* as checked rows (not saved until confirmed)."""
        if not records:
            return
        self._populating = True
        for rec in records:
            row = self._table.rowCount()
            self._table.insertRow(row)
            data = asdict(rec)
            data["id"] = None
            self._set_row(row, data, checked=True, default_source=source)
        self._populating = False
        # New rows follow the active search filter
        self._on_search(self._search.text())
        self._table.scrollToItem(self._table.item(self._table.rowCount() - 1, _COL_TITLE))
        self._update_status()
        self._update_title()

    # ── Editor tools: add entry, CSV import / export ──────────────────────────

    def _on_add_entry(self) -> None:
        dlg = EntryDialog(self)
        dlg.entries_added.connect(
            lambda records: self._append_records(records, SOURCE_MANUAL)
        )
        dlg.exec()
        dlg.deleteLater()

    def _on_import_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, t("csv_import_title"), _default_csv_dir(), t("csv_filter"),
        )
        if not path:
            return
        self.import_csv(Path(path))

    def import_csv(self, path: Path) -> bool:
        """Add the rows of the CSV file *path* to the table; True if rows were added."""
        _remember_csv_dir(path)
        try:
            result = read_csv(path)
        except CsvImportError as exc:
            logger.warning(f"CSV import failed: {path}: {exc.reason} {exc.detail}")
            QMessageBox.warning(self, t("csv_import_title"), self._csv_error_text(exc))
            return False
        logger.info(
            f"CSV read: {path} ({result.encoding}, delimiter {result.delimiter!r}): "
            f"{len(result.records)} rows, {result.skipped} skipped"
        )
        if not result.records:
            QMessageBox.information(
                self, t("csv_import_title"), t("csv_import_none", k=result.skipped)
            )
            return False

        if self._table.rowCount():
            choice = self._ask_append_or_replace(self._table.rowCount())
            if choice is None:
                return False
            if choice == "replace":
                self._table.setRowCount(0)
        self._append_records(result.records, SOURCE_CSV)
        QMessageBox.information(
            self, t("csv_import_title"),
            t("csv_import_done", n=len(result.records), k=result.skipped),
        )
        return True

    @staticmethod
    def _csv_error_text(exc: CsvImportError) -> str:
        if exc.reason == "empty":
            return t("csv_err_empty")
        if exc.reason == "no_title":
            return t("csv_err_no_title", columns=exc.detail or "—")
        return t("csv_err_read", detail=exc.detail)

    def _on_export_csv(self) -> None:
        default = Path(_default_csv_dir()) / default_export_name()
        path, _ = QFileDialog.getSaveFileName(
            self, t("csv_export_title"), str(default), t("csv_filter"),
        )
        if not path:
            return
        target = Path(path)
        if not target.suffix:
            target = target.with_suffix(".csv")
        self.export_csv(target)

    def export_csv(self, path: Path) -> bool:
        """Write every table row (also unchecked and filtered ones) to *path*."""
        _remember_csv_dir(path)
        records = [self._row_to_labelrecord(r) for r in range(self._table.rowCount())]
        try:
            write_csv(path, records)
        except OSError as exc:
            logger.error(f"CSV export failed: {path}: {exc}")
            QMessageBox.critical(
                self, t("csv_export_title"), t("csv_export_err", detail=str(exc))
            )
            return False
        logger.info(f"CSV exported: {len(records)} rows to {path}")
        QMessageBox.information(
            self, t("csv_export_title"),
            t("csv_export_done", n=len(records), path=str(path)),
        )
        return True

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
        # Counts span all rows, not just the visible ones: hidden rows that are
        # checked are still written on confirm.
        total          = self._table.rowCount()
        checked        = 0
        checked_hidden = 0
        incomplete     = 0

        for row in range(total):
            chk = self._table.item(row, _COL_CHECK)
            if chk and chk.checkState() == Qt.CheckState.Checked:
                checked += 1
                if self._table.isRowHidden(row):
                    checked_hidden += 1

            if any(
                not (self._table.item(row, col) and
                     self._table.item(row, col).text().strip())
                for col in _REQUIRED_COLS
            ):
                incomplete += 1

        counts_text = t("review_status_counts", n=total, m=checked)
        if checked_hidden:
            counts_text += f" ({t('review_status_hidden', h=checked_hidden)})"
        self._lbl_status_counts.setText(counts_text)

        colors = current_colors()
        if incomplete:
            self._lbl_status_warning.setText(
                t("review_status_warning", k=incomplete)
            )
            status_color = colors.status_warn if colors else ""
        else:
            self._lbl_status_warning.setText(t("review_status_ok"))
            status_color = colors.status_ok if colors else ""
        if status_color:
            self._lbl_status_warning.setStyleSheet(
                f"color: {status_color}; font-weight: bold;"
            )

        if self._import_mode:
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

    def _on_confirm(self) -> bool:
        """Write the checked rows; return True if saved (the dialog is accepted)."""
        # Visibility is irrelevant here: the queue is written as a whole, so
        # checked rows hidden by the search filter must be kept.
        checked_rows = [
            row for row in range(self._table.rowCount())
            if self._table.item(row, _COL_CHECK) is not None
            and self._table.item(row, _COL_CHECK).checkState() == Qt.CheckState.Checked
        ]

        if not checked_rows and self._import_mode:
            QMessageBox.information(self, t("review_btn_confirm"), t("review_no_sel_msg"))
            return False

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
                return False

        # Rows without a title cannot be stored (an empty side is stored as "A")
        records = [
            rec for rec in (self._row_to_labelrecord(r) for r in checked_rows) if rec.title
        ]

        try:
            if self._import_mode:
                if not records:
                    QMessageBox.information(
                        self, t("review_btn_confirm"), t("review_no_sel_msg")
                    )
                    return False
                choice = "replace"
                existing = self._existing_count()
                if existing:
                    choice = self._ask_append_or_replace(existing)
                    if choice is None:
                        return False
                if choice == "append":
                    label_store.append_to_queue(records, source=self._import_source)
                else:
                    label_store.replace_queue(records, source=self._import_source)
            else:
                if not records:
                    existing = self._existing_count()
                    if existing and not self._confirm_clear(existing):
                        return False
                label_store.replace_queue(records)
        except Exception as exc:
            logger.error(f"Could not write the print queue: {type(exc).__name__}: {exc}")
            QMessageBox.critical(
                self,
                t("discogs_write_err_title"),
                t("discogs_write_err_msg", detail=str(exc)),
            )
            return False

        self._confirmed_records = records
        self._saved = True
        self.accept()
        return True

    def _existing_count(self) -> int:
        try:
            return label_store.queue_count()
        except Exception as exc:
            logger.warning(f"Could not read the print queue: {exc}")
            return 0

    def _confirm_clear(self, n_existing: int) -> bool:
        """Ask before saving an empty selection deletes *n_existing* entries."""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle(t("review_clear_title"))
        msg.setText(t("review_clear_msg", n=n_existing))
        btn_clear = msg.addButton(
            t("review_clear_confirm"), QMessageBox.ButtonRole.DestructiveRole
        )
        btn_back = msg.addButton(t("review_warn_back"), QMessageBox.ButtonRole.RejectRole)
        msg.setDefaultButton(btn_back)
        msg.setEscapeButton(btn_back)
        msg.exec()
        return msg.clickedButton() == btn_clear

    # ── Unsaved changes ───────────────────────────────────────────────────────

    def _table_state(self) -> tuple:
        """Check state and cell texts of all rows, in order (for change detection)."""
        state = []
        for row in range(self._table.rowCount()):
            chk = self._table.item(row, _COL_CHECK)
            checked = chk is not None and chk.checkState() == Qt.CheckState.Checked
            state.append((checked, *self._read_row(row, data_only=True).values()))
        return tuple(state)

    def has_unsaved_changes(self) -> bool:
        return not self._saved and self._table_state() != self._saved_state

    def reject(self) -> None:
        """Cancel, Esc and the window's close button: ask about unsaved changes."""
        if not self.has_unsaved_changes():
            super().reject()
            return
        choice = self._ask_unsaved()
        if choice == "save":
            self._on_confirm()          # accepts the dialog if saving worked
        elif choice == "discard":
            super().reject()
        # "cancel": keep editing

    def _ask_unsaved(self) -> str | None:
        """Return "save", "discard" or None (keep editing)."""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setWindowTitle(t("review_unsaved_title"))
        msg.setText(t("review_unsaved_msg"))
        btn_save = msg.addButton(t("review_unsaved_save"), QMessageBox.ButtonRole.AcceptRole)
        btn_discard = msg.addButton(
            t("review_unsaved_discard"), QMessageBox.ButtonRole.DestructiveRole
        )
        btn_cancel = msg.addButton(t("review_unsaved_cancel"), QMessageBox.ButtonRole.RejectRole)
        msg.setDefaultButton(btn_save)
        msg.setEscapeButton(btn_cancel)
        msg.exec()
        clicked = msg.clickedButton()
        if clicked == btn_save:
            return "save"
        if clicked == btn_discard:
            return "discard"
        return None

    def _ask_append_or_replace(self, n_existing: int) -> str | None:
        """Return "append", "replace" or None (cancel)."""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setWindowTitle(t("review_queue_exists_title"))
        msg.setText(t("review_queue_exists_msg", n=n_existing))
        btn_append  = msg.addButton(
            t("review_queue_append"), QMessageBox.ButtonRole.AcceptRole
        )
        btn_replace = msg.addButton(
            t("review_queue_replace"), QMessageBox.ButtonRole.DestructiveRole
        )
        btn_cancel  = msg.addButton(
            t("review_queue_cancel"), QMessageBox.ButtonRole.RejectRole
        )
        msg.setDefaultButton(btn_append)
        msg.setEscapeButton(btn_cancel)
        msg.exec()
        clicked = msg.clickedButton()
        if clicked == btn_append:
            return "append"
        if clicked == btn_replace:
            return "replace"
        return None

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _read_row(self, row: int, data_only: bool = False) -> dict:
        """Cell texts of *row*; plus its labels.db id and source unless *data_only*."""
        def cell(col: int) -> str:
            item = self._table.item(row, col)
            return item.text() if item else ""

        rec = {
            "title":   cell(_COL_TITLE),
            "artist":  cell(_COL_ARTIST),
            "label":   cell(_COL_LABEL),
            "catno":   cell(_COL_CATNO),
            "country": cell(_COL_COUNTRY),
            "year":    cell(_COL_YEAR),
            "side":    cell(_COL_SIDE),
        }
        if not data_only:
            chk = self._table.item(row, _COL_CHECK)
            row_id = chk.data(_ROLE_ID) if chk else None
            rec["id"] = row_id if isinstance(row_id, int) and row_id >= 0 else None
            rec["source"] = (chk.data(_ROLE_SOURCE) if chk else None) or SOURCE_MANUAL
        return rec

    def _row_to_labelrecord(self, row: int) -> LabelRecord:
        rec = self._read_row(row)
        side = rec["side"].strip()
        return LabelRecord(
            title   = rec["title"].strip(),
            artist  = rec["artist"].strip(),
            label   = rec["label"].strip(),
            country = rec["country"].strip(),
            year    = rec["year"].strip(),
            # Free text like "Side b" is stored as "B"; empty stays empty
            # (flagged by the validation in _on_confirm)
            side    = normalise_side(side) if side else "",
            catno   = rec["catno"].strip(),
            id      = rec["id"],
            source  = rec["source"],
        )

    def get_records(self) -> list[LabelRecord]:
        """Return the confirmed records after the dialog was accepted."""
        return self._confirmed_records

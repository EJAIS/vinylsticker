"""
CollectionDialog — the local record collection (LOCAL mode only).

Opened by "Load data" in LOCAL mode. One row per record of the collection
(labels.db, table records, via modules.label_store):

  A | B | Artist | Title A | Title B | Label | Year | Cat. no. | Country
    | Printed A | Printed B

  • The A / B checkboxes pick the sides to print; a side without a title
    has no checkbox (a greyed "–"). Checked sides hidden by the search stay
    checked.
  • Columns are sortable; the search filters live over all text columns.
    "Only not printed" additionally hides records whose sides with a title
    all have a printed date; "Select all sides" then becomes "Select all
    unprinted sides".
  • "Printed A" / "Printed B" show when a side was last printed (local date
    format). "Mark as printed" / "Mark as not printed" (buttons and context
    menu) set today for every side with a title / clear both sides of the
    selected records.
  • "New record", "Edit" (also double-click) and "Delete" (after a
    confirmation) change the collection at once. Queue rows of a deleted
    record stay in the print queue and only lose their link. If an edit
    changes the data of linked queue rows, one question offers to update
    them too (same transaction); queue_changed is emitted afterwards.
  • "Import CSV" / "Export CSV": the collection CSV (modules.csv_io), one
    row per record. Duplicates (records.duplicate_key) of the collection or
    of earlier rows of the file are skipped or update the existing record,
    after one question for the whole file.
  • "Add to print queue" builds one queue row per checked side and opens the
    ReviewDialog in import mode, like the Discogs import: the user reviews the
    rows and chooses append / replace. When that is confirmed this dialog is
    accepted, and the main window reloads the print queue.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from PyQt6.QtCore import QDate, QLocale, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
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
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from config.themes import ThemeColors
from modules import label_store
from modules.csv_io import (
    CsvImportError,
    default_collection_export_name,
    read_collection_csv,
    write_collection_csv,
)
from modules.i18n import t
from modules.label_store import SOURCE_COLLECTION
from modules.logger import get_logger
from modules.records import CollectionRecord, LabelRecord, printed_date, queue_rows_for_sides
from ui.entry_dialog import EntryDialog
from ui.review_widget import ReviewDialog, default_csv_dir, remember_csv_dir
from ui.theme_manager import ThemedStyles, ThemeManager

logger = get_logger()

# ── Column indices ────────────────────────────────────────────────────────────

_COL_A         = 0
_COL_B         = 1
_COL_ARTIST    = 2
_COL_TITLE_A   = 3
_COL_TITLE_B   = 4
_COL_LABEL     = 5
_COL_YEAR      = 6
_COL_CATNO     = 7
_COL_COUNTRY   = 8
_COL_PRINTED_A = 9
_COL_PRINTED_B = 10
_NUM_COLS      = 11

_SIDE_COLS = {"A": _COL_A, "B": _COL_B}
_PRINTED_COLS = {"A": _COL_PRINTED_A, "B": _COL_PRINTED_B}

# Record id on the items of the A column (moves with its row when sorting)
_ROLE_RECORD_ID = Qt.ItemDataRole.UserRole
# Sort key of the printed date items (ISO date, "" = never)
_ROLE_SORT = Qt.ItemDataRole.UserRole + 1

_PAGE_TABLE = 0
_PAGE_EMPTY = 1


class _DateItem(QTableWidgetItem):
    """A printed date: shown in the locale format, sorted by date."""

    def __init__(self, value: str | None) -> None:
        day = printed_date(value)
        text = ""
        if day is not None:
            text = QLocale().toString(
                QDate(day.year, day.month, day.day), QLocale.FormatType.ShortFormat
            )
        super().__init__(text)
        self.setData(_ROLE_SORT, day.isoformat() if day else "")

    def __lt__(self, other: QTableWidgetItem) -> bool:
        return str(self.data(_ROLE_SORT) or "") < str(other.data(_ROLE_SORT) or "")


class CollectionDialog(QDialog):
    """Table of the collection; "Add to print queue" feeds a ReviewDialog."""

    # Queue rows were changed (a record edit updated its linked rows)
    queue_changed = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._populating = False
        self._records: dict[int, CollectionRecord] = {}
        self._styles = ThemedStyles()

        self.setWindowTitle(t("collection_title"))
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowMinimizeButtonHint
        )
        self.setMinimumSize(720, 480)
        self.resize(1040, 640)
        self.setSizeGripEnabled(True)

        self._build_ui()
        self.reload()
        ThemeManager.instance().theme_changed.connect(self._apply_theme)

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(6)
        root.setContentsMargins(8, 8, 8, 8)

        # ── Record tools + search ─────────────────────────────────────────────
        tools = QHBoxLayout()
        tools.setSpacing(4)
        self._btn_new = QPushButton(t("collection_btn_new"))
        self._btn_new.clicked.connect(self._on_new)
        self._btn_edit = QPushButton(t("collection_btn_edit"))
        self._btn_edit.setToolTip(t("collection_btn_edit_tip"))
        self._btn_edit.clicked.connect(self._on_edit)
        self._btn_delete = QPushButton(t("collection_btn_delete"))
        self._btn_delete.clicked.connect(self._on_delete)
        self._btn_mark_printed = QPushButton(t("collection_btn_mark_printed"))
        self._btn_mark_printed.setToolTip(t("collection_btn_mark_printed_tip"))
        self._btn_mark_printed.clicked.connect(lambda: self.mark_selected(True))
        self._btn_mark_unprinted = QPushButton(t("collection_btn_mark_unprinted"))
        self._btn_mark_unprinted.setToolTip(t("collection_btn_mark_unprinted_tip"))
        self._btn_mark_unprinted.clicked.connect(lambda: self.mark_selected(False))

        self._search = QLineEdit()
        self._search.setPlaceholderText(t("collection_search_ph"))
        self._search.setClearButtonEnabled(True)
        self._search.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._search.textChanged.connect(self._apply_filter)

        for w in (
            self._btn_new, self._btn_edit, self._btn_delete,
            self._btn_mark_printed, self._btn_mark_unprinted,
        ):
            tools.addWidget(w)
        tools.addStretch()
        tools.addWidget(self._search)
        root.addLayout(tools)

        # ── Side selection, printed filter, CSV ───────────────────────────────
        selection = QHBoxLayout()
        selection.setSpacing(4)
        self._btn_all = QPushButton(t("collection_btn_all"))
        self._btn_all.setToolTip(t("collection_btn_all_tip"))
        self._btn_all.clicked.connect(lambda: self._set_all_checked(True))
        self._btn_none = QPushButton(t("collection_btn_none"))
        self._btn_none.clicked.connect(lambda: self._set_all_checked(False))
        self._chk_unprinted = QCheckBox(t("collection_chk_unprinted"))
        self._chk_unprinted.setToolTip(t("collection_chk_unprinted_tip"))
        self._chk_unprinted.toggled.connect(self._on_unprinted_toggled)
        self._btn_import = QPushButton(t("collection_btn_import_csv"))
        self._btn_import.setToolTip(t("collection_btn_import_csv_tip"))
        self._btn_import.clicked.connect(self._on_import_csv)
        self._btn_export = QPushButton(t("collection_btn_export_csv"))
        self._btn_export.setToolTip(t("collection_btn_export_csv_tip"))
        self._btn_export.clicked.connect(self._on_export_csv)
        selection.addWidget(self._btn_all)
        selection.addWidget(self._btn_none)
        selection.addSpacing(12)
        selection.addWidget(self._chk_unprinted)
        selection.addStretch()
        selection.addWidget(self._btn_import)
        selection.addWidget(self._btn_export)
        root.addLayout(selection)

        # ── Table / empty hint ────────────────────────────────────────────────
        self._stack = QStackedWidget()

        self._table = QTableWidget(0, _NUM_COLS)
        self._table.setHorizontalHeaderLabels([
            t("collection_col_a"),
            t("collection_col_b"),
            t("collection_col_artist"),
            t("collection_col_title_a"),
            t("collection_col_title_b"),
            t("collection_col_label"),
            t("collection_col_year"),
            t("collection_col_catno"),
            t("collection_col_country"),
            t("collection_col_printed_a"),
            t("collection_col_printed_b"),
        ])
        hdr = self._table.horizontalHeader()
        for col in (_COL_A, _COL_B):
            hdr.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            self._table.setColumnWidth(col, 36)
            header_item = self._table.horizontalHeaderItem(col)
            if header_item:
                header_item.setToolTip(t("collection_col_side_tip"))
        for col in (_COL_ARTIST, _COL_TITLE_A, _COL_TITLE_B, _COL_LABEL):
            hdr.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        for col in (_COL_YEAR, _COL_CATNO, _COL_COUNTRY, _COL_PRINTED_A, _COL_PRINTED_B):
            hdr.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        for col in _PRINTED_COLS.values():
            header_item = self._table.horizontalHeaderItem(col)
            if header_item:
                header_item.setToolTip(t("collection_col_printed_tip"))
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.setSortingEnabled(True)
        self._table.sortByColumn(_COL_ARTIST, Qt.SortOrder.AscendingOrder)
        self._table.itemChanged.connect(self._on_item_changed)
        self._table.itemDoubleClicked.connect(self._on_double_clicked)
        self._table.itemSelectionChanged.connect(self._update_buttons)
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._on_context_menu)
        self._stack.addWidget(self._table)

        empty = QWidget()
        empty_layout = QVBoxLayout(empty)
        empty_layout.addStretch()
        self._lbl_empty = QLabel(t("collection_empty"))
        self._lbl_empty.setWordWrap(True)
        self._lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._styles.add(self._lbl_empty, lambda c: f"color: {c.text_secondary};")
        self._btn_empty_new = QPushButton(t("collection_btn_new"))
        self._btn_empty_new.setProperty("primary", True)
        self._btn_empty_new.clicked.connect(self._on_new)
        empty_layout.addWidget(self._lbl_empty)
        empty_layout.addWidget(self._btn_empty_new, 0, Qt.AlignmentFlag.AlignHCenter)
        empty_layout.addStretch()
        self._stack.addWidget(empty)

        root.addWidget(self._stack, 1)

        # ── Status + bottom buttons ───────────────────────────────────────────
        self._lbl_status = QLabel("")
        self._styles.add(self._lbl_status, lambda c: f"color: {c.text_secondary};")
        root.addWidget(self._lbl_status)

        buttons = QHBoxLayout()
        btn_close = QPushButton(t("collection_btn_close"))
        btn_close.clicked.connect(self.reject)
        self._btn_queue = QPushButton(t("collection_btn_to_queue"))
        self._btn_queue.setToolTip(t("collection_btn_to_queue_tip"))
        self._btn_queue.setProperty("primary", True)
        self._btn_queue.setDefault(True)
        self._btn_queue.clicked.connect(self._on_add_to_queue)
        buttons.addWidget(btn_close)
        buttons.addStretch()
        buttons.addWidget(self._btn_queue)
        root.addLayout(buttons)

    # ── Loading / table population ────────────────────────────────────────────

    def reload(self, select_id: int | None = None) -> None:
        """(Re)load the collection; keep the checked sides and the search filter."""
        checked = self.checked_sides()
        try:
            records = label_store.list_records()
        except Exception as exc:
            logger.error(f"Could not load the collection: {type(exc).__name__}: {exc}")
            QMessageBox.critical(
                self, t("collection_title"), t("collection_load_err", detail=str(exc))
            )
            records = []
        self._records = {record.id: record for record in records}

        self._populating = True
        sort_col = self._table.horizontalHeader().sortIndicatorSection()
        sort_order = self._table.horizontalHeader().sortIndicatorOrder()
        self._table.setSortingEnabled(False)
        self._table.setRowCount(0)
        for record in records:
            row = self._table.rowCount()
            self._table.insertRow(row)
            self._set_row(row, record, checked.get(record.id, set()))
        self._table.setSortingEnabled(True)
        self._table.sortByColumn(sort_col, sort_order)
        self._populating = False

        self._stack.setCurrentIndex(_PAGE_TABLE if records else _PAGE_EMPTY)
        self._apply_filter(self._search.text())
        if select_id is not None:
            self._select_record(select_id)
        self._update_buttons()

    def _set_row(self, row: int, record: CollectionRecord, checked: set[str]) -> None:
        for side, col in _SIDE_COLS.items():
            if record.title(side):
                item = QTableWidgetItem()
                item.setFlags(
                    Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsSelectable
                    | Qt.ItemFlag.ItemIsEnabled
                )
                item.setCheckState(
                    Qt.CheckState.Checked if side in checked else Qt.CheckState.Unchecked
                )
                item.setToolTip(t("collection_side_tip", side=side))
            else:
                # Disabled: no checkbox (an unthemed disabled indicator looks
                # like an enabled one), a greyed dash instead
                item = QTableWidgetItem("–")
                item.setFlags(Qt.ItemFlag.ItemIsSelectable)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setToolTip(t("collection_side_no_title", side=side))
            item.setData(_ROLE_RECORD_ID, record.id)
            self._table.setItem(row, col, item)

        for col, value in (
            (_COL_ARTIST, record.artist),
            (_COL_TITLE_A, record.title_a),
            (_COL_TITLE_B, record.title_b),
            (_COL_LABEL, record.label),
            (_COL_YEAR, record.year),
            (_COL_CATNO, record.catno),
            (_COL_COUNTRY, record.country),
        ):
            item = QTableWidgetItem(value)
            item.setData(_ROLE_RECORD_ID, record.id)
            self._table.setItem(row, col, item)

        for side, col in _PRINTED_COLS.items():
            item = _DateItem(record.printed_at(side))
            item.setData(_ROLE_RECORD_ID, record.id)
            self._table.setItem(row, col, item)

    def _record_id(self, row: int) -> int | None:
        item = self._table.item(row, _COL_A)
        value = item.data(_ROLE_RECORD_ID) if item else None
        return value if isinstance(value, int) else None

    def _row_of(self, record_id: int) -> int | None:
        for row in range(self._table.rowCount()):
            if self._record_id(row) == record_id:
                return row
        return None

    def _select_record(self, record_id: int) -> None:
        row = self._row_of(record_id)
        if row is not None:
            self._table.selectRow(row)
            self._table.scrollToItem(self._table.item(row, _COL_ARTIST))

    # ── Selection of sides ────────────────────────────────────────────────────

    def checked_sides(self) -> dict[int, set[str]]:
        """{record id: checked sides} over all rows (also hidden ones)."""
        result: dict[int, set[str]] = {}
        for row in range(self._table.rowCount()):
            record_id = self._record_id(row)
            if record_id is None:
                continue
            for side, col in _SIDE_COLS.items():
                item = self._table.item(row, col)
                if item and item.checkState() == Qt.CheckState.Checked:
                    result.setdefault(record_id, set()).add(side)
        return result

    def set_side_checked(self, record_id: int, side: str, checked: bool) -> bool:
        """Check / uncheck one side; False if the side cannot be checked."""
        row = self._row_of(record_id)
        if row is None:
            return False
        item = self._table.item(row, _SIDE_COLS[side])
        if item is None or not (item.flags() & Qt.ItemFlag.ItemIsUserCheckable):
            return False
        item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        return True

    def _set_all_checked(self, checked: bool) -> None:
        """Select all sides of the visible rows, or clear the whole selection.

        With "Only not printed" only the unprinted sides are selected.
        """
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        only_unprinted = self._chk_unprinted.isChecked()
        self._populating = True
        for row in range(self._table.rowCount()):
            # "Select all" follows the search filter; "Clear" clears everything
            if checked and self._table.isRowHidden(row):
                continue
            record = self._records.get(self._record_id(row))
            for side, col in _SIDE_COLS.items():
                if checked and only_unprinted and (
                    record is None or side not in record.unprinted_sides()
                ):
                    continue
                item = self._table.item(row, col)
                if item and item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                    item.setCheckState(state)
        self._populating = False
        self._update_buttons()

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if not self._populating and item.column() in _SIDE_COLS.values():
            self._update_buttons()

    # ── Search ────────────────────────────────────────────────────────────────

    def _apply_filter(self, text: str | None = None) -> None:
        """Show the rows matching the search *text* and the "Only not printed" filter."""
        text = self._search.text() if text is None else text
        if text.strip():
            try:
                visible = {record.id for record in label_store.list_records(text)}
            except Exception as exc:
                logger.warning(f"Collection search failed: {exc}")
                visible = set(self._records)
        else:
            visible = set(self._records)
        if self._chk_unprinted.isChecked():
            visible = {
                record_id for record_id in visible
                if record_id in self._records and self._records[record_id].unprinted_sides()
            }
        for row in range(self._table.rowCount()):
            self._table.setRowHidden(row, self._record_id(row) not in visible)
        self._update_buttons()

    def _on_unprinted_toggled(self, checked: bool) -> None:
        key = "collection_btn_all_unprinted" if checked else "collection_btn_all"
        self._btn_all.setText(t(key))
        self._btn_all.setToolTip(t(key + "_tip"))
        self._apply_filter()

    # ── Printed marks ─────────────────────────────────────────────────────────

    def _on_context_menu(self, pos) -> None:
        row = self._table.rowAt(pos.y())
        if row < 0:
            return
        if self._record_id(row) not in self._selected_ids():
            self._table.selectRow(row)
        menu = QMenu(self)
        act_printed = menu.addAction(t("collection_btn_mark_printed"))
        act_unprinted = menu.addAction(t("collection_btn_mark_unprinted"))
        chosen = menu.exec(self._table.viewport().mapToGlobal(pos))
        if chosen == act_printed:
            self.mark_selected(True)
        elif chosen == act_unprinted:
            self.mark_selected(False)

    def mark_selected(self, printed: bool) -> None:
        """Mark the selected records as printed today (every side with a title) / not printed."""
        selected = self._selected_ids()
        if not selected:
            return
        try:
            if printed:
                label_store.mark_records_printed(selected)
            else:
                label_store.clear_printed(selected)
        except Exception as exc:
            self._write_error(exc)
            return
        self.reload()
        self._reselect(selected)

    def _reselect(self, record_ids: list[int]) -> None:
        """Select the visible rows of *record_ids* again (after a reload)."""
        self._table.clearSelection()
        mode = self._table.selectionMode()
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        for record_id in record_ids:
            row = self._row_of(record_id)
            if row is not None and not self._table.isRowHidden(row):
                self._table.selectRow(row)
        self._table.setSelectionMode(mode)

    # ── Buttons / status ──────────────────────────────────────────────────────

    def _selected_ids(self) -> list[int]:
        rows = sorted({index.row() for index in self._table.selectedIndexes()})
        return [
            record_id for record_id in (self._record_id(row) for row in rows
                                        if not self._table.isRowHidden(row))
            if record_id is not None
        ]

    def _update_buttons(self) -> None:
        n_sides = hidden = 0
        for row in range(self._table.rowCount()):
            for col in _SIDE_COLS.values():
                item = self._table.item(row, col)
                if item and item.checkState() == Qt.CheckState.Checked:
                    n_sides += 1
                    hidden += self._table.isRowHidden(row)
        selected = self._selected_ids()
        has_records = bool(self._records)
        self._btn_edit.setEnabled(len(selected) == 1)
        self._btn_delete.setEnabled(bool(selected))
        self._btn_mark_printed.setEnabled(bool(selected))
        self._btn_mark_unprinted.setEnabled(bool(selected))
        self._btn_all.setEnabled(has_records)
        self._btn_none.setEnabled(n_sides > 0)
        self._search.setEnabled(has_records)
        self._chk_unprinted.setEnabled(has_records or self._chk_unprinted.isChecked())
        self._btn_export.setEnabled(has_records)
        self._btn_queue.setEnabled(n_sides > 0)

        status = t("collection_status", n=len(self._records), m=n_sides)
        if hidden:
            status += f" ({t('review_status_hidden', h=hidden)})"
        self._lbl_status.setText(status)

    def _apply_theme(self, colors: ThemeColors | None = None) -> None:
        colors = colors or ThemeManager.instance().colors
        if colors is not None:
            self._styles.apply(colors)

    # ── New / edit / delete ───────────────────────────────────────────────────

    def _edit_record(self, record: CollectionRecord | None) -> CollectionRecord | None:
        """Open the record form; return the entered record, or None (cancelled)."""
        dlg = EntryDialog(self, record_mode=True, record=record)
        accepted = dlg.exec() == QDialog.DialogCode.Accepted
        result = dlg.record() if accepted else None
        dlg.deleteLater()
        return result

    def _on_new(self) -> None:
        record = self._edit_record(None)
        if record is None:
            return
        try:
            record_id = label_store.add_record(record)
        except Exception as exc:
            self._write_error(exc)
            return
        self.reload(select_id=record_id)

    def _on_edit(self) -> None:
        selected = self._selected_ids()
        if len(selected) == 1:
            self.edit_record_id(selected[0])

    def _on_double_clicked(self, item: QTableWidgetItem) -> None:
        if item.column() not in _SIDE_COLS.values():
            record_id = self._record_id(item.row())
            if record_id is not None:
                self.edit_record_id(record_id)

    def edit_record_id(self, record_id: int) -> None:
        current = self._records.get(record_id)
        if current is None:
            return
        record = self._edit_record(current)
        if record is None:
            return
        try:
            to_sync = label_store.queue_rows_to_sync(record)
            sync = bool(to_sync) and self._ask_update_queue(len(to_sync))
            synced = label_store.update_record(record, sync_queue=sync)
        except Exception as exc:
            self._write_error(exc)
            return
        self.reload(select_id=record_id)
        if synced:
            self.queue_changed.emit()

    def _ask_update_queue(self, n_rows: int) -> bool:
        """Ask whether the *n_rows* linked queue rows should get the edited data too."""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setWindowTitle(t("collection_sync_queue_title"))
        msg.setText(t("collection_sync_queue_msg", n=n_rows))
        btn_yes = msg.addButton(t("btn_yes"), QMessageBox.ButtonRole.YesRole)
        btn_no = msg.addButton(t("btn_no"), QMessageBox.ButtonRole.NoRole)
        msg.setDefaultButton(btn_yes)
        msg.setEscapeButton(btn_no)
        msg.exec()
        return msg.clickedButton() == btn_yes

    def _on_delete(self) -> None:
        selected = self._selected_ids()
        if not selected or not self._confirm_delete(selected):
            return
        try:
            label_store.delete_records(selected)
        except Exception as exc:
            self._write_error(exc)
            return
        self.reload()

    def _confirm_delete(self, record_ids: list[int]) -> bool:
        if len(record_ids) == 1:
            record = self._records[record_ids[0]]
            name = " / ".join(title for title in (record.title_a, record.title_b) if title)
            if record.artist:
                name = f"{record.artist} – {name}"
            text = t("collection_delete_one", name=name)
        else:
            text = t("collection_delete_many", n=len(record_ids))
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle(t("collection_delete_title"))
        msg.setText(text + "\n\n" + t("collection_delete_queue_note"))
        btn_delete = msg.addButton(
            t("collection_delete_confirm"), QMessageBox.ButtonRole.DestructiveRole
        )
        btn_cancel = msg.addButton(t("review_queue_cancel"), QMessageBox.ButtonRole.RejectRole)
        msg.setDefaultButton(btn_cancel)
        msg.setEscapeButton(btn_cancel)
        msg.exec()
        return msg.clickedButton() == btn_delete

    def _write_error(self, exc: Exception) -> None:
        logger.error(f"Could not write the collection: {type(exc).__name__}: {exc}")
        QMessageBox.critical(
            self, t("collection_title"), t("collection_write_err", detail=str(exc))
        )

    # ── CSV import / export ───────────────────────────────────────────────────

    def _on_import_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, t("csv_import_title"), default_csv_dir(), t("csv_filter"),
        )
        if path:
            self.import_csv(Path(path))

    def import_csv(self, path: Path) -> bool:
        """Import the collection CSV *path*; True if the collection was written."""
        remember_csv_dir(path)
        try:
            result = read_collection_csv(path)
        except CsvImportError as exc:
            logger.warning(f"Collection CSV import failed: {path}: {exc.reason} {exc.detail}")
            QMessageBox.warning(self, t("csv_import_title"), self._csv_error_text(exc))
            return False
        logger.info(
            f"Collection CSV read: {path} ({result.encoding}, delimiter "
            f"{result.delimiter!r}): {len(result.records)} rows, {result.skipped} skipped"
        )
        if not result.records:
            QMessageBox.information(
                self, t("csv_import_title"), t("collection_csv_none", k=result.skipped)
            )
            return False
        try:
            n_duplicates = label_store.count_duplicates(result.records)
        except Exception as exc:
            self._write_error(exc)
            return False
        update_existing = False
        if n_duplicates:
            choice = self._ask_duplicates(n_duplicates)
            if choice is None:
                return False
            update_existing = choice == "update"
        try:
            counts = label_store.import_records(result.records, update_existing)
        except Exception as exc:
            self._write_error(exc)
            return False
        self.reload()
        message = t(
            "collection_csv_import_done",
            i=counts.imported, u=counts.updated, s=counts.skipped + result.skipped,
        )
        if counts.unchanged:
            message += "\n" + t("collection_csv_import_unchanged", c=counts.unchanged)
        QMessageBox.information(self, t("csv_import_title"), message)
        return True

    @staticmethod
    def _csv_error_text(exc: CsvImportError) -> str:
        if exc.reason == "empty":
            return t("csv_err_empty")
        if exc.reason == "no_title":
            return t("collection_csv_err_no_title", columns=exc.detail or "—")
        return t("csv_err_read", detail=exc.detail)

    def _ask_duplicates(self, n_duplicates: int) -> str | None:
        """Return "skip", "update" or None (cancel the import)."""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setWindowTitle(t("collection_csv_dup_title"))
        msg.setText(t("collection_csv_dup_msg", n=n_duplicates))
        btn_skip = msg.addButton(t("collection_csv_dup_skip"), QMessageBox.ButtonRole.AcceptRole)
        btn_update = msg.addButton(
            t("collection_csv_dup_update"), QMessageBox.ButtonRole.AcceptRole
        )
        btn_cancel = msg.addButton(t("review_queue_cancel"), QMessageBox.ButtonRole.RejectRole)
        msg.setDefaultButton(btn_skip)
        msg.setEscapeButton(btn_cancel)
        msg.exec()
        clicked = msg.clickedButton()
        if clicked == btn_skip:
            return "skip"
        if clicked == btn_update:
            return "update"
        return None

    def _on_export_csv(self) -> None:
        default = Path(default_csv_dir()) / default_collection_export_name()
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
        """Write every record of the collection (regardless of the filters) to *path*."""
        remember_csv_dir(path)
        try:
            records = label_store.list_records()
            write_collection_csv(path, records)
        except Exception as exc:
            logger.error(f"Collection CSV export failed: {path}: {exc}")
            QMessageBox.critical(
                self, t("csv_export_title"), t("csv_export_err", detail=str(exc))
            )
            return False
        logger.info(f"Collection CSV exported: {len(records)} records to {path}")
        QMessageBox.information(
            self, t("csv_export_title"),
            t("collection_csv_export_done", n=len(records), path=str(path)),
        )
        return True

    # ── Add to print queue ────────────────────────────────────────────────────

    def build_queue_rows(self) -> list[LabelRecord]:
        """One queue row per checked side, in table order (A before B)."""
        checked = self.checked_sides()
        rows: list[LabelRecord] = []
        for row in range(self._table.rowCount()):
            record_id = self._record_id(row)
            record = self._records.get(record_id) if record_id is not None else None
            if record is not None and record_id in checked:
                rows.extend(queue_rows_for_sides(record, checked[record_id]))
        return rows

    def _on_add_to_queue(self) -> None:
        rows = self.build_queue_rows()
        if not rows:
            return
        dlg = ReviewDialog(
            [asdict(row) for row in rows],
            import_mode=True,
            import_source=SOURCE_COLLECTION,
            parent=self,
        )
        accepted = dlg.exec() == QDialog.DialogCode.Accepted
        dlg.deleteLater()
        if accepted:
            self.accept()

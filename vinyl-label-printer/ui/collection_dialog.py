"""
CollectionDialog — the local record collection (LOCAL mode only).

Opened by "Load data" in LOCAL mode. One row per record of the collection
(labels.db, table records, via modules.label_store):

  A | B | Artist | Title A | Title B | Label | Year | Cat. no. | Country

  • The A / B checkboxes pick the sides to print; a side without a title
    has no checkbox (a greyed "–"). Checked sides hidden by the search stay
    checked.
  • Columns are sortable; the search filters live over all text columns.
  • "New record", "Edit" (also double-click) and "Delete" (after a
    confirmation) change the collection at once. Queue rows of a deleted
    record stay in the print queue and only lose their link.
  • "Add to print queue" builds one queue row per checked side and opens the
    ReviewDialog in import mode, like the Discogs import: the user reviews the
    rows and chooses append / replace. When that is confirmed this dialog is
    accepted, and the main window reloads the print queue.
"""

from __future__ import annotations

from dataclasses import asdict

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
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
from modules.i18n import t
from modules.label_store import SOURCE_COLLECTION
from modules.logger import get_logger
from modules.records import CollectionRecord, LabelRecord, queue_rows_for_sides
from ui.entry_dialog import EntryDialog
from ui.review_widget import ReviewDialog
from ui.theme_manager import ThemedStyles, ThemeManager

logger = get_logger()

# ── Column indices ────────────────────────────────────────────────────────────

_COL_A       = 0
_COL_B       = 1
_COL_ARTIST  = 2
_COL_TITLE_A = 3
_COL_TITLE_B = 4
_COL_LABEL   = 5
_COL_YEAR    = 6
_COL_CATNO   = 7
_COL_COUNTRY = 8
_NUM_COLS    = 9

_SIDE_COLS = {"A": _COL_A, "B": _COL_B}

# Record id on the items of the A column (moves with its row when sorting)
_ROLE_RECORD_ID = Qt.ItemDataRole.UserRole

_PAGE_TABLE = 0
_PAGE_EMPTY = 1


class CollectionDialog(QDialog):
    """Table of the collection; "Add to print queue" feeds a ReviewDialog."""

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

        self._search = QLineEdit()
        self._search.setPlaceholderText(t("collection_search_ph"))
        self._search.setClearButtonEnabled(True)
        self._search.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._search.textChanged.connect(self._apply_filter)

        for w in (self._btn_new, self._btn_edit, self._btn_delete):
            tools.addWidget(w)
        tools.addStretch()
        tools.addWidget(self._search)
        root.addLayout(tools)

        # ── Side selection ────────────────────────────────────────────────────
        selection = QHBoxLayout()
        selection.setSpacing(4)
        self._btn_all = QPushButton(t("collection_btn_all"))
        self._btn_all.setToolTip(t("collection_btn_all_tip"))
        self._btn_all.clicked.connect(lambda: self._set_all_checked(True))
        self._btn_none = QPushButton(t("collection_btn_none"))
        self._btn_none.clicked.connect(lambda: self._set_all_checked(False))
        selection.addWidget(self._btn_all)
        selection.addWidget(self._btn_none)
        selection.addStretch()
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
        for col in (_COL_YEAR, _COL_CATNO, _COL_COUNTRY):
            hdr.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.setSortingEnabled(True)
        self._table.sortByColumn(_COL_ARTIST, Qt.SortOrder.AscendingOrder)
        self._table.itemChanged.connect(self._on_item_changed)
        self._table.itemDoubleClicked.connect(self._on_double_clicked)
        self._table.itemSelectionChanged.connect(self._update_buttons)
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
        """Select all sides of the visible rows, or clear the whole selection."""
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        self._populating = True
        for row in range(self._table.rowCount()):
            # "Select all" follows the search filter; "Clear" clears everything
            if checked and self._table.isRowHidden(row):
                continue
            for col in _SIDE_COLS.values():
                item = self._table.item(row, col)
                if item and item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                    item.setCheckState(state)
        self._populating = False
        self._update_buttons()

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if not self._populating and item.column() in _SIDE_COLS.values():
            self._update_buttons()

    # ── Search ────────────────────────────────────────────────────────────────

    def _apply_filter(self, text: str) -> None:
        if text.strip():
            try:
                visible = {record.id for record in label_store.list_records(text)}
            except Exception as exc:
                logger.warning(f"Collection search failed: {exc}")
                visible = set(self._records)
        else:
            visible = set(self._records)
        for row in range(self._table.rowCount()):
            self._table.setRowHidden(row, self._record_id(row) not in visible)
        self._update_buttons()

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
        self._btn_all.setEnabled(has_records)
        self._btn_none.setEnabled(n_sides > 0)
        self._search.setEnabled(has_records)
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
            label_store.update_record(record)
        except Exception as exc:
            self._write_error(exc)
            return
        self.reload(select_id=record_id)

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

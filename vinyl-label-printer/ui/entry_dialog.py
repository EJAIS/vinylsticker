"""
EntryDialog — small form for one record (side A and / or side B).

Artist, Label, Country, Year and Catalog number are shared by both sides. At
least one title is required, the year is empty or four digits.

Two modes share the same fields and validation:
  • Queue mode (default): adds rows to the print queue editor (ReviewDialog);
    each filled title becomes one row with side A or B. "Add" emits the rows
    and closes the form; "Add and next" emits them, clears the form and puts
    the focus back on the first field. The rows are only added to the editor's
    table — they are saved together with the rest when the user confirms the
    editor. With *collection_option* (LOCAL mode) the form shows "Also save to
    collection" (last state remembered in the settings); the editor then
    links the rows to a new collection record, written on confirm as well.
  • Record mode: creates or edits one record of the local collection
    (CollectionDialog); "Save" validates and accepts, the caller writes it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from config.settings import get_save_to_collection, set_save_to_collection
from config.themes import ThemeColors
from modules.i18n import t
from modules.label_store import SOURCE_MANUAL
from modules.records import CollectionRecord, LabelRecord
from ui.theme_manager import ThemedStyles, ThemeManager

_YEAR_RE = re.compile(r"\d{4}")


@dataclass
class EntryInput:
    """The form values (stripped)."""
    artist:  str = ""
    label:   str = ""
    country: str = ""
    year:    str = ""
    catno:   str = ""
    title_a: str = ""
    title_b: str = ""


def validate_entry(entry: EntryInput) -> str | None:
    """Return the i18n key of the first problem, or None if *entry* is valid."""
    if not entry.title_a and not entry.title_b:
        return "entry_err_no_title"
    if entry.year and not _YEAR_RE.fullmatch(entry.year):
        return "entry_err_year"
    return None


def entry_from_record(record: CollectionRecord) -> EntryInput:
    """The form values of a collection record."""
    return EntryInput(
        artist=record.artist, label=record.label, country=record.country,
        year=record.year, catno=record.catno,
        title_a=record.title_a, title_b=record.title_b,
    )


def record_from_entry(
    entry: EntryInput, base: CollectionRecord | None = None
) -> CollectionRecord:
    """A collection record with the form values; id and timestamps from *base*."""
    record = CollectionRecord(
        artist=entry.artist, label=entry.label, country=entry.country,
        year=entry.year, catno=entry.catno,
        title_a=entry.title_a, title_b=entry.title_b,
    )
    if base is not None:
        record.id = base.id
        record.printed_a_at = base.printed_a_at
        record.printed_b_at = base.printed_b_at
        record.created_at = base.created_at
        record.updated_at = base.updated_at
    return record


def entry_records(entry: EntryInput) -> list[LabelRecord]:
    """One record per filled title (A first), sharing the other fields."""
    records = []
    for side, title in (("A", entry.title_a), ("B", entry.title_b)):
        if title:
            records.append(LabelRecord(
                title=title,
                artist=entry.artist,
                label=entry.label,
                country=entry.country,
                year=entry.year,
                side=side,
                catno=entry.catno,
                source=SOURCE_MANUAL,
            ))
    return records


class EntryDialog(QDialog):
    """Form for one record.

    Queue mode: emits entries_added(list[LabelRecord]) per add. Record mode
    (*record_mode*): edits *record* (None: a new one), read it with record()
    after the dialog was accepted.
    """

    entries_added = pyqtSignal(list)

    def __init__(
        self,
        parent=None,
        collection_option: bool = False,
        record_mode: bool = False,
        record: CollectionRecord | None = None,
    ) -> None:
        super().__init__(parent)
        self._record_mode = record_mode
        self._collection_option = collection_option and not record_mode
        self._base_record = record
        if record_mode:
            self.setWindowTitle(t("record_title_edit" if record else "record_title_new"))
        else:
            self.setWindowTitle(t("entry_title"))
        self.setModal(True)
        self.setMinimumWidth(420)
        self._styles = ThemedStyles()

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        form = QFormLayout()
        form.setSpacing(8)
        self._edit_artist = QLineEdit()
        self._edit_label = QLineEdit()
        self._edit_country = QLineEdit()
        self._edit_year = QLineEdit()
        self._edit_year.setMaxLength(4)
        self._edit_year.setPlaceholderText(t("entry_ph_year"))
        self._edit_catno = QLineEdit()
        self._edit_title_a = QLineEdit()
        self._edit_title_b = QLineEdit()
        for key, edit in (
            ("entry_lbl_artist", self._edit_artist),
            ("entry_lbl_label", self._edit_label),
            ("entry_lbl_country", self._edit_country),
            ("entry_lbl_year", self._edit_year),
            ("entry_lbl_catno", self._edit_catno),
            ("entry_lbl_title_a", self._edit_title_a),
            ("entry_lbl_title_b", self._edit_title_b),
        ):
            form.addRow(t(key), edit)
        root.addLayout(form)

        # "Also save to collection" (queue mode in LOCAL mode only)
        self._chk_collection = QCheckBox(t("entry_save_to_collection"))
        self._chk_collection.setToolTip(t("entry_save_to_collection_tip"))
        self._chk_collection.setVisible(self._collection_option)
        if self._collection_option:
            self._chk_collection.setChecked(get_save_to_collection())
            self._chk_collection.toggled.connect(set_save_to_collection)
        root.addWidget(self._chk_collection)

        self._lbl_hint = QLabel(t("record_hint" if record_mode else "entry_hint"))
        self._lbl_hint.setWordWrap(True)
        self._styles.add(self._lbl_hint, lambda c: f"color: {c.text_muted};")
        root.addWidget(self._lbl_hint)

        # Validation error or "n rows added" feedback
        self._lbl_message = QLabel("")
        self._lbl_message.setWordWrap(True)
        self._message_role = "danger"
        self._styles.add(
            self._lbl_message,
            lambda c: f"color: {getattr(c, self._message_role)}; font-weight: bold;",
        )
        root.addWidget(self._lbl_message)

        buttons = QHBoxLayout()
        btn_cancel = QPushButton(t("record_btn_cancel" if record_mode else "entry_btn_close"))
        btn_cancel.clicked.connect(self.reject)
        self._btn_add_next = QPushButton(t("entry_btn_add_next"))
        self._btn_add_next.setAutoDefault(False)
        self._btn_add_next.clicked.connect(self._on_add_next)
        self._btn_add_next.setVisible(not record_mode)
        self._btn_add = QPushButton(t("record_btn_save" if record_mode else "entry_btn_add"))
        self._btn_add.setDefault(True)
        self._btn_add.setProperty("primary", True)
        self._btn_add.clicked.connect(self._on_add)
        buttons.addWidget(btn_cancel)
        buttons.addStretch()
        buttons.addWidget(self._btn_add_next)
        buttons.addWidget(self._btn_add)
        root.addLayout(buttons)

        if record is not None:
            self.set_entry(entry_from_record(record))
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._edit_artist.setFocus(Qt.FocusReason.OtherFocusReason)

    # ── Form values ───────────────────────────────────────────────────────────

    def _edits(self) -> tuple[QLineEdit, ...]:
        return (
            self._edit_artist, self._edit_label, self._edit_country, self._edit_year,
            self._edit_catno, self._edit_title_a, self._edit_title_b,
        )

    def entry(self) -> EntryInput:
        return EntryInput(*(edit.text().strip() for edit in self._edits()))

    def set_entry(self, entry: EntryInput) -> None:
        values = (
            entry.artist, entry.label, entry.country, entry.year,
            entry.catno, entry.title_a, entry.title_b,
        )
        for edit, value in zip(self._edits(), values):
            edit.setText(value)

    def save_to_collection(self) -> bool:
        """Queue mode: whether the added rows also go to the collection."""
        return self._collection_option and self._chk_collection.isChecked()

    def record(self) -> CollectionRecord:
        """Record mode: the edited record (id and timestamps of the given one)."""
        return record_from_entry(self.entry(), self._base_record)

    # ── Actions ───────────────────────────────────────────────────────────────

    def _validate(self) -> bool:
        """Show the first problem of the form; return True if it is valid."""
        error = validate_entry(self.entry())
        if error:
            self._show_message(t(error), "danger")
            (self._edit_year if error == "entry_err_year" else self._edit_title_a).setFocus()
            return False
        return True

    def _submit(self) -> bool:
        """Validate and emit the rows; return True if rows were added."""
        if not self._validate():
            return False
        records = entry_records(self.entry())
        self.entries_added.emit(records)
        self._show_message(t("entry_added", n=len(records)), "status_ok")
        return True

    def _on_add(self) -> None:
        if self._record_mode:
            if self._validate():
                self.accept()
        elif self._submit():
            self.accept()

    def _on_add_next(self) -> None:
        if self._submit():
            for edit in self._edits():
                edit.clear()
            self._edit_artist.setFocus(Qt.FocusReason.OtherFocusReason)

    def _show_message(self, text: str, role: str) -> None:
        self._message_role = role
        self._lbl_message.setText(text)
        self._apply_theme()

    def _apply_theme(self, colors: ThemeColors | None = None) -> None:
        colors = colors or ThemeManager.instance().colors
        if colors is not None:
            self._styles.apply(colors)

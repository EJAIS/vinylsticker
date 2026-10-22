"""
EntryDialog — small form to add one record (side A and / or side B) to the
print queue editor (ReviewDialog).

Artist, Label, Country, Year and Catalog number are shared by both sides; each
filled title becomes one row with side A or B. At least one title is required,
the year is empty or four digits.

"Add" emits the rows and closes the form; "Add and next" emits them, clears
the form and puts the focus back on the first field. The rows are only added
to the editor's table — they are saved together with the rest when the user
confirms the editor.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from config.themes import ThemeColors
from modules.i18n import t
from modules.label_store import SOURCE_MANUAL
from modules.records import LabelRecord
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
    """Form for one record; emits entries_added(list[LabelRecord]) per add."""

    entries_added = pyqtSignal(list)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
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

        self._lbl_hint = QLabel(t("entry_hint"))
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
        btn_cancel = QPushButton(t("entry_btn_close"))
        btn_cancel.clicked.connect(self.reject)
        self._btn_add_next = QPushButton(t("entry_btn_add_next"))
        self._btn_add_next.setAutoDefault(False)
        self._btn_add_next.clicked.connect(self._on_add_next)
        self._btn_add = QPushButton(t("entry_btn_add"))
        self._btn_add.setDefault(True)
        self._btn_add.setProperty("primary", True)
        self._btn_add.clicked.connect(self._on_add)
        buttons.addWidget(btn_cancel)
        buttons.addStretch()
        buttons.addWidget(self._btn_add_next)
        buttons.addWidget(self._btn_add)
        root.addLayout(buttons)

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

    # ── Actions ───────────────────────────────────────────────────────────────

    def _submit(self) -> bool:
        """Validate and emit the rows; return True if rows were added."""
        entry = self.entry()
        error = validate_entry(entry)
        if error:
            self._show_message(t(error), "danger")
            (self._edit_year if error == "entry_err_year" else self._edit_title_a).setFocus()
            return False
        records = entry_records(entry)
        self.entries_added.emit(records)
        self._show_message(t("entry_added", n=len(records)), "status_ok")
        return True

    def _on_add(self) -> None:
        if self._submit():
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

"""
Keyboard shortcut helpers.

keys() prefers a QKeySequence standard key (Find, New, Delete, Print, …) so
platform conventions (e.g. Cmd on macOS) stay correct, and falls back to an
explicit sequence where the platform defines none. add_shortcut() creates a
QShortcut for all of them; with_shortcut() appends the first one, in the
platform's native notation, to a tooltip: "Print (Ctrl+P)" (further bindings
of a standard key, e.g. a dedicated "New" key, still work but are not shown).

Table cell editors: EditorShortcutGuard is installed on every editor of a
table (see the delegate of the queue editor); it claims all key presses while
an editor is open, so no shortcut of the dialog fires during editing.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from PyQt6.QtCore import QEvent, QObject, Qt
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import QAbstractItemView, QWidget

StandardKey = QKeySequence.StandardKey


def keys(standard: StandardKey | None = None, *fallback: str) -> list[QKeySequence]:
    """The key sequences of *standard* on this platform, else the *fallback* sequences."""
    sequences = QKeySequence.keyBindings(standard) if standard is not None else []
    sequences = [seq for seq in sequences if not seq.isEmpty()]
    return sequences or [QKeySequence(text) for text in fallback]


def shortcut_text(sequences: Sequence[QKeySequence]) -> str:
    """The sequences in native notation, e.g. "Ctrl+P" or "Enter, F2"."""
    return ", ".join(
        seq.toString(QKeySequence.SequenceFormat.NativeText) for seq in sequences
    )


def with_shortcut(text: str, sequences: Sequence[QKeySequence], shown: int = 1) -> str:
    """*text* with the first *shown* sequences appended: "Print (Ctrl+P)"."""
    hint = shortcut_text(sequences[:shown])
    return f"{text} ({hint})" if hint else text


def plain(text: str) -> str:
    """A button text without trailing ellipsis / arrow, for use in a tooltip."""
    return text.rstrip(" …→.").strip()


def add_shortcut(
    parent: QWidget,
    sequences: Sequence[QKeySequence],
    slot: Callable[[], object],
    context: Qt.ShortcutContext = Qt.ShortcutContext.WindowShortcut,
) -> QShortcut:
    """A QShortcut on *parent* for all *sequences* that calls *slot*."""
    shortcut = QShortcut(parent)
    shortcut.setKeys(list(sequences))
    shortcut.setContext(context)
    shortcut.activated.connect(slot)
    return shortcut


def is_editing(view: QAbstractItemView) -> bool:
    """Whether a cell editor of *view* is open."""
    return view.state() == QAbstractItemView.State.EditingState


class EditorShortcutGuard(QObject):
    """Event filter for cell editors: the editor gets every key, no shortcut fires."""

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802
        if event.type() == QEvent.Type.ShortcutOverride:
            # Accepting the override hands the key to the editor as a key press
            event.accept()
            return True
        return False

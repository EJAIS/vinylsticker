"""
Label records and side normalisation, without any storage dependency.

LabelRecord is the unit everything else works with: the print queue in
labels.db (modules.label_store), the PDF generator, the Discogs import, the CSV
import / export and the review dialog.

CollectionRecord is one record of the local collection (LOCAL mode): the
shared print data plus a title per side. A queue row can link to the side of
a collection record it was made from (record_id / record_side).
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

SIDES = ("A", "B")

# Field order of the print data, also the column order of the CSV export
RECORD_FIELDS = ("title", "artist", "label", "country", "year", "side", "catno")


@dataclass
class LabelRecord:
    title:   str
    artist:  str
    label:   str
    country: str
    year:    str
    side:    str   # always "A" or "B" after normalisation
    catno:   str = ""
    # Where the row comes from in labels.db; not part of the label, so two
    # records with the same print data compare equal.
    id:      int | None = field(default=None, compare=False)
    source:  str = field(default="", compare=False)
    # Link to the collection record side this row was made from (LOCAL mode);
    # None for Discogs rows, one-off entries and rows from 1.1. Not printed.
    record_id:   int | None = field(default=None, compare=False)
    record_side: str | None = field(default=None, compare=False)
    # A collection record that is created together with this row when the
    # queue is saved (queue editor, "Also save to collection"); never stored
    # as such — label_store writes it and links the row to the new id.
    pending_record: CollectionRecord | None = field(
        default=None, compare=False, repr=False
    )


@dataclass
class CollectionRecord:
    """One record of the local collection; at least one title is required."""
    artist:  str = ""
    label:   str = ""
    country: str = ""
    year:    str = ""
    catno:   str = ""
    title_a: str = ""
    title_b: str = ""
    id:      int | None = field(default=None, compare=False)
    # When a side was last printed (ISO timestamps); the UI comes in part 2
    printed_a_at: str | None = field(default=None, compare=False)
    printed_b_at: str | None = field(default=None, compare=False)
    created_at:   str = field(default="", compare=False)
    updated_at:   str = field(default="", compare=False)

    def title(self, side: str) -> str:
        """Title of *side* ("A" / "B")."""
        return self.title_a if side == "A" else self.title_b


def queue_rows_for_sides(record: CollectionRecord, sides: Iterable[str]) -> list[LabelRecord]:
    """One queue row per side in *sides* that has a title, A before B.

    Each row carries the title of its side, the shared fields and the link
    (record_id / record_side) to *record*.
    """
    wanted = set(sides)
    return [
        LabelRecord(
            title=record.title(side),
            artist=record.artist,
            label=record.label,
            country=record.country,
            year=record.year,
            side=side,
            catno=record.catno,
            record_id=record.id,
            record_side=side,
        )
        for side in SIDES
        if side in wanted and record.title(side)
    ]


def record_from_rows(rows: Sequence[LabelRecord]) -> CollectionRecord:
    """A collection record from the queue rows of one record.

    The shared fields come from the first row; each side's title from the
    first row of that side (record_side, else side).
    """
    first = rows[0] if rows else LabelRecord("", "", "", "", "", "A")
    record = CollectionRecord(
        artist=first.artist, label=first.label, country=first.country,
        year=first.year, catno=first.catno,
    )
    for row in rows:
        side = normalise_side(row.record_side or row.side)
        if side == "A" and not record.title_a:
            record.title_a = row.title
        elif side == "B" and not record.title_b:
            record.title_b = row.title
    return record


def _shared_key(row: LabelRecord) -> tuple[str, ...]:
    return tuple(
        (value or "").strip()
        for value in (row.artist, row.label, row.country, row.year, row.catno)
    )


def group_rows_into_records(rows: Sequence[LabelRecord]) -> list[list[int]]:
    """Group imported queue rows into collection records (indices into *rows*).

    An A row directly followed by a B row with identical artist, label,
    country, year and catalog number (after trimming) is one record with both
    titles; every other row is a record with only its own side.
    """
    groups: list[list[int]] = []
    index = 0
    while index < len(rows):
        row = rows[index]
        following = rows[index + 1] if index + 1 < len(rows) else None
        if (
            following is not None
            and normalise_side(row.side) == "A"
            and normalise_side(following.side) == "B"
            and _shared_key(row) == _shared_key(following)
        ):
            groups.append([index, index + 1])
            index += 2
        else:
            groups.append([index])
            index += 1
    return groups


_SIDE_PREFIX_RE = re.compile(r"^(?:SEITE|SIDE|[\s\-:])+")


def resolve_side(value: object) -> str | None:
    """Return "A" or "B" for *value*, or None if it names no A/B side.

    Same rules as normalise_side() but without the "A" default, e.g.
    "C1", "D" or "3" → None.
    """
    raw = str(value).strip().upper() if value is not None else ""
    raw = _SIDE_PREFIX_RE.sub("", raw)
    if not raw:
        return None
    if raw.startswith("AA"):
        return "B"
    if raw[0] in ("A", "B"):
        return raw[0]
    # Fallback: take the last character that is A or B
    for ch in reversed(raw):
        if ch in ("A", "B"):
            return ch
    return None


def normalise_side(value: object) -> str:
    """Normalise a side / track position to a single uppercase 'A' or 'B'.

    Rules (case-insensitive, trimmed):
      • Prefixes "Seite", "Side", "-", ":" and whitespace are removed.
      • "AA…" (UK double-A side) → "B".
      • Starts with "A" → "A" (A, A1, A2); starts with "B" → "B".
      • Otherwise the last A/B character wins; failing that, "A".

    Examples::

        normalise_side("A")       # → "A"
        normalise_side("AA")      # → "B"
        normalise_side("A2")      # → "A"
        normalise_side("B2")      # → "B"
        normalise_side("Seite B") # → "B"
        normalise_side("side a")  # → "A"
        normalise_side("")        # → "A"
    """
    return resolve_side(value) or "A"

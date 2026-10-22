"""
Label records and side normalisation, without any storage dependency.

LabelRecord is the unit everything else works with: the print queue in
labels.db (modules.label_store), the PDF generator, the Discogs import, the CSV
import / export and the review dialog.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

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

"""
Excel reader module.

Loads label records from the "Print" and "Database" sheets of the project
Excel file.  The "Database" sheet is always opened read-only.

Column layout (A–G): Title, Artist, Label, Country, Year, Side, CatNo.
Files without column G (CatNo) load with an empty catalog number.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import openpyxl

from modules.logger import get_logger

logger = get_logger()

SHEET_PRINT    = "Print"
SHEET_DATABASE = "Database"
COLUMNS        = ("Title", "Artist", "Label", "Country", "Year", "Side", "CatNo")


@dataclass
class LabelRecord:
    title:   str
    artist:  str
    label:   str
    country: str
    year:    str
    side:    str   # always "A" or "B" after normalisation
    catno:   str = ""


# ── Public helpers ────────────────────────────────────────────────────────────

def load_print_queue(xlsx_path: Path) -> list[LabelRecord]:
    """Read the 'Print' sheet and return all non-empty rows as LabelRecords.

    The workbook is opened with data_only=True so formula cells resolve to
    their cached value rather than the formula string.
    """
    try:
        wb = openpyxl.load_workbook(str(xlsx_path), data_only=True)
        ws = wb[SHEET_PRINT]
        records = _read_sheet(ws)
        wb.close()
    except Exception as e:
        logger.error(f"Excel error loading {xlsx_path}: {e}")
        raise
    logger.info(f"Excel loaded: {len(records)} records from print queue")
    return records


def write_print_queue(xlsx_path: Path, records: list[LabelRecord]) -> None:
    """Overwrite the 'Print' sheet with *records*.

    The sheet is cleared and rewritten with a header row followed by one
    data row per record.  All other sheets in the workbook are untouched.
    """
    wb = openpyxl.load_workbook(str(xlsx_path))
    ws = wb[SHEET_PRINT]
    ws.delete_rows(1, ws.max_row)          # clear all existing rows
    ws.append(list(COLUMNS))              # write header
    for rec in records:
        ws.append([
            rec.title, rec.artist, rec.label, rec.country, rec.year, rec.side, rec.catno,
        ])
    wb.save(str(xlsx_path))
    wb.close()


def load_database(xlsx_path: Path) -> list[LabelRecord]:
    """Read the 'Database' sheet (read-only, never modified).

    Opens the workbook in read_only mode for efficiency.
    """
    try:
        wb = openpyxl.load_workbook(str(xlsx_path), read_only=True, data_only=True)
        ws = wb[SHEET_DATABASE]
        records = _read_sheet(ws)
        wb.close()
    except Exception as e:
        logger.error(f"Excel error loading {xlsx_path}: {e}")
        raise
    logger.info(f"Database loaded: {len(records)} records")
    return records


# ── Internal helpers ──────────────────────────────────────────────────────────

def _read_sheet(ws) -> list[LabelRecord]:
    """Iterate rows of *ws*, skip the header row, return LabelRecords."""
    records: list[LabelRecord] = []
    for row_idx, row in enumerate(ws.iter_rows(values_only=True)):
        if row_idx == 0:
            # Skip header row (Title, Artist, …)
            continue
        record = _row_to_record(row)
        if record is not None:
            records.append(record)
    return records


def _row_to_record(row: tuple) -> LabelRecord | None:
    """Convert an openpyxl row tuple into a LabelRecord.

    Returns None for rows where the Title cell is empty/None so that blank
    rows at the bottom of the sheet are silently ignored.
    """
    # Pad to at least 7 elements — older files have no CatNo column (G)
    cells = list(row) + [None] * 7
    title, artist, label, country, year, side, catno = cells[:7]

    # Skip rows with no title
    if title is None or str(title).strip() == "":
        return None

    return LabelRecord(
        title=_str(title),
        artist=_str(artist),
        label=_str(label),
        country=_str(country),
        year=_str(year),
        side=normalise_side(side),
        catno=_str(catno),
    )


def _str(value: object) -> str:
    """Convert a cell value to a stripped string, defaulting to ''."""
    if value is None:
        return ""
    return str(value).strip()


_SIDE_PREFIX_RE = re.compile(r"^(?:SEITE|SIDE|[\s\-:])+")


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
    raw = str(value).strip().upper() if value is not None else ""
    raw = _SIDE_PREFIX_RE.sub("", raw)
    if not raw:
        return "A"
    if raw.startswith("AA"):
        return "B"
    if raw[0] in ("A", "B"):
        return raw[0]
    # Fallback: take the last character that is A or B
    for ch in reversed(raw):
        if ch in ("A", "B"):
            return ch
    return "A"

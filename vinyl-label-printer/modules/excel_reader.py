"""
Read-only reader for the database.xlsx of versions before 1.1.

Only used once, by the migration into labels.db (modules.xlsx_migration).
The workbook is opened read-only and is never written.

Column layout (A–G): Title, Artist, Label, Country, Year, Side, CatNo.
Files without column G (CatNo) load with an empty catalog number.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import openpyxl

from modules.logger import get_logger
from modules.records import LabelRecord, normalise_side

logger = get_logger()

SHEET_PRINT    = "Print"
SHEET_DATABASE = "Database"


@dataclass
class LegacyWorkbook:
    """Content of a legacy database.xlsx."""
    print_records: list[LabelRecord]
    # Rows with a title in the "Database" sheet; None if there is no such sheet
    database_rows: int | None


def read_legacy_workbook(xlsx_path: Path) -> LegacyWorkbook:
    """Read the 'Print' sheet as LabelRecords and count the 'Database' rows.

    The workbook is opened with read_only=True (never modified) and
    data_only=True so formula cells resolve to their cached value.

    Raises:
        KeyError: if the workbook has no 'Print' sheet.
        Exception: whatever openpyxl raises for an unreadable file.
    """
    wb = openpyxl.load_workbook(str(xlsx_path), read_only=True, data_only=True)
    try:
        records = _read_sheet(wb[SHEET_PRINT])
        database_rows = (
            len(_read_sheet(wb[SHEET_DATABASE]))
            if SHEET_DATABASE in wb.sheetnames else None
        )
    finally:
        wb.close()
    logger.info(f"Legacy workbook read: {len(records)} records in the Print sheet")
    return LegacyWorkbook(records, database_rows)


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

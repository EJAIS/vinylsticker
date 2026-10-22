"""
CSV import and export of print queue rows — the way to bulk-edit and back up
the print queue outside the app.

Import
  • Encoding: UTF-8 (with or without BOM), otherwise Windows-1252.
  • Delimiter: comma, semicolon or tab — whichever occurs most in the header.
  • The first row is the header. Columns are matched by name, case-insensitive,
    ignoring spaces, dots, hyphens and underscores; unknown columns are ignored.
    English: Title, Artist, Label, Country, Year, Side, CatNo
    German:  Titel, Künstler / Kuenstler / Interpret, Label, Land, Jahr, Seite,
             Katalognummer
  • A Title column is required. Without a Side column every row is side A;
    sides go through normalise_side().
  • Rows with an empty title are skipped and counted; completely empty rows
    are ignored.

Export
  English header, semicolon, UTF-8 with BOM (opens correctly in Excel and
  LibreOffice). Exported files import back to identical rows.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from modules.records import LabelRecord, normalise_side

EXPORT_HEADER = ("Title", "Artist", "Label", "Country", "Year", "Side", "CatNo")
EXPORT_DELIMITER = ";"
EXPORT_ENCODING = "utf-8-sig"
_DELIMITERS = (",", ";", "\t")

# Normalised header name → LabelRecord field
_HEADER_ALIASES: dict[str, str] = {
    "title": "title", "titel": "title",
    "artist": "artist", "künstler": "artist", "kuenstler": "artist",
    "interpret": "artist",
    "label": "label",
    "country": "country", "land": "country",
    "year": "year", "jahr": "year",
    "side": "side", "seite": "side",
    "catno": "catno", "katalognummer": "catno",
}
_HEADER_NOISE = re.compile(r"[\s._\-]+")


class CsvImportError(ValueError):
    """The file cannot be imported. *reason*: "empty" | "no_title" | "read"."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(detail or reason)
        self.reason = reason
        self.detail = detail


@dataclass
class CsvImportResult:
    records: list[LabelRecord] = field(default_factory=list)
    skipped: int = 0            # rows with content but without a title
    encoding: str = ""
    delimiter: str = ""


def _decode(data: bytes) -> tuple[str, str]:
    """Return (text, encoding name) — UTF-8 (BOM optional), else Windows-1252."""
    try:
        return data.decode("utf-8-sig"), "utf-8-sig"
    except UnicodeDecodeError:
        # cp1252 leaves five bytes undefined; replace them instead of failing
        return data.decode("cp1252", errors="replace"), "cp1252"


def _detect_delimiter(header_line: str) -> str:
    counts = {d: header_line.count(d) for d in _DELIMITERS}
    best = max(_DELIMITERS, key=lambda d: counts[d])
    return best if counts[best] else ","


def _normalise_header(name: str) -> str:
    return _HEADER_NOISE.sub("", name.strip().casefold())


def map_header(header: list[str]) -> dict[str, int]:
    """Return {LabelRecord field: column index}; the first matching column wins."""
    mapping: dict[str, int] = {}
    for index, name in enumerate(header):
        target = _HEADER_ALIASES.get(_normalise_header(name))
        if target and target not in mapping:
            mapping[target] = index
    return mapping


def parse_csv_text(text: str) -> CsvImportResult:
    """Parse CSV *text* (already decoded) into LabelRecords.

    Raises:
        CsvImportError: no header row, or no Title column.
    """
    first_line = text.splitlines()[0] if text.strip() else ""
    if not first_line.strip():
        raise CsvImportError("empty")
    delimiter = _detect_delimiter(first_line)
    rows = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter)
    header = next(rows, [])
    columns = map_header(header)
    if "title" not in columns:
        found = ", ".join(name.strip() for name in header if name.strip())
        raise CsvImportError("no_title", found)

    result = CsvImportResult(delimiter=delimiter)
    for row in rows:
        if not any(cell.strip() for cell in row):
            continue

        def cell(name: str) -> str:
            index = columns.get(name)
            if index is None or index >= len(row):
                return ""
            return row[index].strip()

        title = cell("title")
        if not title:
            result.skipped += 1
            continue
        result.records.append(LabelRecord(
            title=title,
            artist=cell("artist"),
            label=cell("label"),
            country=cell("country"),
            year=cell("year"),
            side=normalise_side(cell("side")),
            catno=cell("catno"),
        ))
    return result


def read_csv(path: Path) -> CsvImportResult:
    """Import *path*; see the module docstring for the accepted format.

    Raises:
        CsvImportError: unreadable file, no header row, or no Title column.
    """
    try:
        data = Path(path).read_bytes()
    except OSError as exc:
        raise CsvImportError("read", str(exc)) from exc
    text, encoding = _decode(data)
    try:
        result = parse_csv_text(text)
    except csv.Error as exc:
        raise CsvImportError("read", str(exc)) from exc
    result.encoding = encoding
    return result


def write_csv(path: Path, records: list[LabelRecord]) -> None:
    """Export *records* (English header, semicolon, UTF-8 with BOM)."""
    with open(path, "w", encoding=EXPORT_ENCODING, newline="") as handle:
        writer = csv.writer(handle, delimiter=EXPORT_DELIMITER)
        writer.writerow(EXPORT_HEADER)
        for rec in records:
            writer.writerow([
                rec.title, rec.artist, rec.label, rec.country, rec.year, rec.side, rec.catno,
            ])


def default_export_name(today: date | None = None) -> str:
    """vinyl-labels-YYYY-MM-DD.csv"""
    return f"vinyl-labels-{(today or date.today()).isoformat()}.csv"

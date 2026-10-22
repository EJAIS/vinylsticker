"""
CSV import and export of print queue rows — the way to bulk-edit and back up
the print queue outside the app — and of the local collection (records).

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
  English header, semicolon, UTF-8 with BOM (umlauts show correctly in
  spreadsheet programs). Exported files import back to identical rows.

Collection CSV (one row per record instead of one per label)
  Header: Artist;Label;Country;Year;CatNo;TitleA;TitleB;PrintedA;PrintedB
  German: Künstler / Interpret, Label, Land, Jahr, Katalognummer, Titel A,
          Titel B, Gedruckt A, Gedruckt B
  Same encoding, delimiter and header matching as above. A TitleA or TitleB
  column is required; rows without any title are skipped and counted. Printed
  dates are ISO dates (YYYY-MM-DD) or empty; on import DD.MM.YYYY (as a
  German spreadsheet program saves dates) and ISO timestamps are accepted too,
  anything else counts as empty. Export: same format as the queue export, all
  records, printed dates as local ISO dates.

Formula protection (both formats)
  A spreadsheet program runs a cell that starts with = + - @ (or a tab /
  carriage return in front of one) as a formula. On export such a cell gets a
  leading apostrophe, which the spreadsheet shows as text; on import exactly
  that one apostrophe is removed again. A value that itself starts with
  apostrophes in front of one of these characters gets one more, so every
  value survives the round trip unchanged. Any other apostrophe stays.
"""

from __future__ import annotations

import csv
import io
import re
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from modules.logger import get_logger
from modules.records import CollectionRecord, LabelRecord, normalise_side, printed_date

logger = get_logger()

EXPORT_HEADER = ("Title", "Artist", "Label", "Country", "Year", "Side", "CatNo")
COLLECTION_EXPORT_HEADER = (
    "Artist", "Label", "Country", "Year", "CatNo", "TitleA", "TitleB", "PrintedA", "PrintedB",
)
EXPORT_DELIMITER = ";"
EXPORT_ENCODING = "utf-8-sig"
_DELIMITERS = (",", ";", "\t")
# First characters a spreadsheet program may treat as the start of a formula
_FORMULA_START = ("=", "+", "-", "@", "\t", "\r")

# Normalised header name → LabelRecord / CollectionRecord field
_HEADER_ALIASES: dict[str, str] = {
    "title": "title", "titel": "title",
    "artist": "artist", "künstler": "artist", "kuenstler": "artist",
    "interpret": "artist",
    "label": "label",
    "country": "country", "land": "country",
    "year": "year", "jahr": "year",
    "side": "side", "seite": "side",
    "catno": "catno", "katalognummer": "catno",
    # Collection CSV
    "titlea": "title_a", "titela": "title_a",
    "titleb": "title_b", "titelb": "title_b",
    "printeda": "printed_a_at", "gedruckta": "printed_a_at",
    "printedb": "printed_b_at", "gedrucktb": "printed_b_at",
}
_HEADER_NOISE = re.compile(r"[\s._\-]+")


class CsvImportError(ValueError):
    """The file cannot be imported. *reason*: "empty" | "no_title" | "read".

    "no_title": no Title column (queue), no TitleA / TitleB column (collection).
    """

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


@dataclass
class CollectionCsvResult:
    records: list[CollectionRecord] = field(default_factory=list)
    skipped: int = 0            # rows with content but without any title
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


def _escape_cell(value: str) -> str:
    """Prefix *value* with an apostrophe if a spreadsheet could run it as a formula.

    Leading apostrophes are looked through, so a value like "'=x" gets one
    more too and _unescape_cell() returns every value unchanged.
    """
    if value.lstrip("'").startswith(_FORMULA_START):
        return "'" + value
    return value


def _unescape_cell(value: str) -> str:
    """Remove the one apostrophe _escape_cell() put in front of *value*, if any."""
    if value.startswith("'") and value.lstrip("'").startswith(_FORMULA_START):
        return value[1:]
    return value


def _write_row(writer, cells: Sequence[str]) -> None:
    writer.writerow([_escape_cell(str(cell)) for cell in cells])


def _table(
    text: str, required: Sequence[str]
) -> tuple[str, Iterator[dict[str, str]]]:
    """(delimiter, one {field: trimmed cell} per non-empty data row) of CSV *text*.

    Raises:
        CsvImportError: no header row, or none of the *required* fields.
    """
    first_line = text.splitlines()[0] if text.strip() else ""
    if not first_line.strip():
        raise CsvImportError("empty")
    delimiter = _detect_delimiter(first_line)
    rows = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter)
    header = next(rows, [])
    columns = map_header(header)
    if not any(name in columns for name in required):
        found = ", ".join(name.strip() for name in header if name.strip())
        raise CsvImportError("no_title", found)

    def cells() -> Iterator[dict[str, str]]:
        for row in rows:
            if any(cell.strip() for cell in row):
                yield {
                    name: _unescape_cell(row[index].strip()) if index < len(row) else ""
                    for name, index in columns.items()
                }

    return delimiter, cells()


def _read_text(path: Path) -> tuple[str, str]:
    """(text, encoding) of *path*; raises CsvImportError("read")."""
    try:
        data = Path(path).read_bytes()
    except OSError as exc:
        raise CsvImportError("read", str(exc)) from exc
    return _decode(data)


def parse_csv_text(text: str) -> CsvImportResult:
    """Parse CSV *text* (already decoded) into LabelRecords.

    Raises:
        CsvImportError: no header row, or no Title column.
    """
    delimiter, rows = _table(text, ("title",))
    result = CsvImportResult(delimiter=delimiter)
    for row in rows:
        title = row.get("title", "")
        if not title:
            result.skipped += 1
            continue
        result.records.append(LabelRecord(
            title=title,
            artist=row.get("artist", ""),
            label=row.get("label", ""),
            country=row.get("country", ""),
            year=row.get("year", ""),
            side=normalise_side(row.get("side", "")),
            catno=row.get("catno", ""),
        ))
    return result


def read_csv(path: Path) -> CsvImportResult:
    """Import *path*; see the module docstring for the accepted format.

    Raises:
        CsvImportError: unreadable file, no header row, or no Title column.
    """
    text, encoding = _read_text(path)
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
            _write_row(writer, [
                rec.title, rec.artist, rec.label, rec.country, rec.year, rec.side, rec.catno,
            ])


def default_export_name(today: date | None = None) -> str:
    """vinyl-labels-YYYY-MM-DD.csv"""
    return f"vinyl-labels-{(today or date.today()).isoformat()}.csv"


# ── Collection CSV ────────────────────────────────────────────────────────────

def _parse_printed(value: str) -> str | None:
    """An ISO date (YYYY-MM-DD) from a PrintedA / PrintedB cell, None if empty / invalid."""
    value = value.strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, "%d.%m.%Y").date().isoformat()
    except ValueError:
        pass
    day = printed_date(value)
    if day is None:
        logger.warning(f"Collection CSV: unreadable printed date {value!r} ignored")
        return None
    return day.isoformat()


def parse_collection_csv_text(text: str) -> CollectionCsvResult:
    """Parse collection CSV *text* (already decoded) into CollectionRecords.

    Raises:
        CsvImportError: no header row, or neither a TitleA nor a TitleB column.
    """
    delimiter, rows = _table(text, ("title_a", "title_b"))
    result = CollectionCsvResult(delimiter=delimiter)
    for row in rows:
        record = CollectionRecord(
            artist=row.get("artist", ""),
            label=row.get("label", ""),
            country=row.get("country", ""),
            year=row.get("year", ""),
            catno=row.get("catno", ""),
            title_a=row.get("title_a", ""),
            title_b=row.get("title_b", ""),
            printed_a_at=_parse_printed(row.get("printed_a_at", "")),
            printed_b_at=_parse_printed(row.get("printed_b_at", "")),
        )
        if not record.title_a and not record.title_b:
            result.skipped += 1
            continue
        result.records.append(record)
    return result


def read_collection_csv(path: Path) -> CollectionCsvResult:
    """Import the collection CSV *path*; see the module docstring.

    Raises:
        CsvImportError: unreadable file, no header row, or no title column.
    """
    text, encoding = _read_text(path)
    try:
        result = parse_collection_csv_text(text)
    except csv.Error as exc:
        raise CsvImportError("read", str(exc)) from exc
    result.encoding = encoding
    return result


def _printed_cell(value: str | None) -> str:
    day = printed_date(value)
    return day.isoformat() if day else ""


def write_collection_csv(path: Path, records: Sequence[CollectionRecord]) -> None:
    """Export *records*, one row per record (English header, semicolon, UTF-8 with BOM)."""
    with open(path, "w", encoding=EXPORT_ENCODING, newline="") as handle:
        writer = csv.writer(handle, delimiter=EXPORT_DELIMITER)
        writer.writerow(COLLECTION_EXPORT_HEADER)
        for rec in records:
            _write_row(writer, [
                rec.artist, rec.label, rec.country, rec.year, rec.catno,
                rec.title_a, rec.title_b,
                _printed_cell(rec.printed_a_at), _printed_cell(rec.printed_b_at),
            ])


def default_collection_export_name(today: date | None = None) -> str:
    """vinyl-collection-YYYY-MM-DD.csv"""
    return f"vinyl-collection-{(today or date.today()).isoformat()}.csv"

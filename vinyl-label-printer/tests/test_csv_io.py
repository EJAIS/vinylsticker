"""CSV import (delimiters, headers, encodings) and export -> import round trip."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from modules.csv_io import (
    CsvImportError,
    default_export_name,
    read_csv,
    write_csv,
)
from modules.records import LabelRecord

_ROWS = [
    LabelRecord("Song A", "Artist 1", "Label 1", "UK", "1969", "A", "R 5001"),
    LabelRecord("Song B", "Artist 1", "Label 1", "UK", "1969", "B", "R 5001"),
]


def _write(path: Path, text: str, encoding: str = "utf-8") -> Path:
    path.write_bytes(text.encode(encoding))
    return path


@pytest.mark.parametrize("delimiter", [",", ";", "\t"])
def test_delimiters(tmp_path, delimiter):
    lines = [
        ["Title", "Artist", "Label", "Country", "Year", "Side", "CatNo"],
        ["Song A", "Artist 1", "Label 1", "UK", "1969", "A", "R 5001"],
        ["Song B", "Artist 1", "Label 1", "UK", "1969", "B", "R 5001"],
    ]
    text = "\r\n".join(delimiter.join(cells) for cells in lines) + "\r\n"
    result = read_csv(_write(tmp_path / "in.csv", text))
    assert result.delimiter == delimiter
    assert result.records == _ROWS
    assert result.skipped == 0


def test_german_header_any_order_and_case(tmp_path):
    text = (
        "seite;KÜNSTLER;Titel;Land;Jahr;Label;Katalognummer;Notiz\n"
        "A;Artist 1;Song A;UK;1969;Label 1;R 5001;ignored\n"
        "Seite B;Artist 1;Song B;UK;1969;Label 1;R 5001;ignored\n"
    )
    assert read_csv(_write(tmp_path / "in.csv", text)).records == _ROWS


@pytest.mark.parametrize("artist_header", ["Kuenstler", "Interpret", "Künstler", "artist"])
def test_artist_aliases(tmp_path, artist_header):
    text = f"Titel,{artist_header}\nSong,Someone\n"
    record = read_csv(_write(tmp_path / "in.csv", text)).records[0]
    assert (record.title, record.artist) == ("Song", "Someone")


def test_utf8_with_bom(tmp_path):
    text = "Title;Artist;Side\nÜber;Mötley Crüe;B\n"
    result = read_csv(_write(tmp_path / "in.csv", text, "utf-8-sig"))
    assert result.encoding == "utf-8-sig"
    assert (result.records[0].title, result.records[0].artist) == ("Über", "Mötley Crüe")
    assert result.records[0].side == "B"


def test_cp1252_fallback(tmp_path):
    text = "Titel;Künstler;Land\nÜber;Mötley Crüe – Live;Österreich\n"
    result = read_csv(_write(tmp_path / "in.csv", text, "cp1252"))
    assert result.encoding == "cp1252"
    rec = result.records[0]
    assert (rec.title, rec.artist, rec.country) == ("Über", "Mötley Crüe – Live", "Österreich")


def test_missing_side_column_means_side_a(tmp_path):
    text = "Title,Artist\nOne,X\nTwo,Y\n"
    assert [r.side for r in read_csv(_write(tmp_path / "in.csv", text)).records] == ["A", "A"]


def test_sides_are_normalised(tmp_path):
    text = "Title;Side\na;b2\nb;Side B\nc;AA\nd;\ne;A1\n"
    sides = [r.side for r in read_csv(_write(tmp_path / "in.csv", text)).records]
    assert sides == ["B", "B", "B", "A", "A"]


def test_empty_titles_are_skipped_and_counted(tmp_path):
    text = (
        "Title;Artist\n"
        "One;X\n"
        ";no title\n"
        "   ;blank title\n"
        ";;\n"                 # completely empty: ignored, not counted
        "\n"
        "Two;Y\n"
    )
    result = read_csv(_write(tmp_path / "in.csv", text))
    assert [r.title for r in result.records] == ["One", "Two"]
    assert result.skipped == 2


def test_short_rows_and_quoted_values(tmp_path):
    text = 'Title,Artist,Label\n"Hello, Goodbye",The Beatles\n"Say ""Hi""",X,"L; 1"\n'
    records = read_csv(_write(tmp_path / "in.csv", text)).records
    assert (records[0].title, records[0].artist, records[0].label) == (
        "Hello, Goodbye", "The Beatles", "",
    )
    assert (records[1].title, records[1].label) == ('Say "Hi"', "L; 1")


def test_header_without_title_column(tmp_path):
    with pytest.raises(CsvImportError) as info:
        read_csv(_write(tmp_path / "in.csv", "Song;Artist\nOne;X\n"))
    assert info.value.reason == "no_title"
    assert info.value.detail == "Song, Artist"


def test_empty_file(tmp_path):
    with pytest.raises(CsvImportError) as info:
        read_csv(_write(tmp_path / "in.csv", ""))
    assert info.value.reason == "empty"


def test_missing_file(tmp_path):
    with pytest.raises(CsvImportError) as info:
        read_csv(tmp_path / "missing.csv")
    assert info.value.reason == "read"


def test_export_format(tmp_path):
    out = tmp_path / "out.csv"
    write_csv(out, _ROWS)
    data = out.read_bytes()
    assert data.startswith(b"\xef\xbb\xbf")                       # UTF-8 BOM
    assert data.decode("utf-8-sig").splitlines()[0] == (
        "Title;Artist;Label;Country;Year;Side;CatNo"
    )


def test_export_import_round_trip(tmp_path):
    records = _ROWS + [
        LabelRecord('Say "Hi"; now', "Mötley Crüe", "Label, Inc.", "Österreich",
                    "", "B", "Ä-1;2"),
        LabelRecord("Tab\there", "", "", "", "2001", "A", ""),
        LabelRecord("No other fields", "", "", "", "", "A", ""),
        # Formula protection: values a spreadsheet would run as a formula
        LabelRecord("=1+1", "-", "+44", "@home", "-1", "A", "'quoted"),
        LabelRecord("'=already quoted", "''=twice", "\tTab first", "\rCR first",
                    "", "B", "it's"),
    ]
    out = tmp_path / "out.csv"
    write_csv(out, records)
    result = read_csv(out)
    assert result.records == records
    assert result.skipped == 0
    assert result.delimiter == ";"


def test_default_export_name():
    assert default_export_name(date(2026, 10, 22)) == "vinyl-labels-2026-10-22.csv"


def test_export_protects_formula_cells(tmp_path):
    out = tmp_path / "out.csv"
    write_csv(out, [
        LabelRecord("=1+1", "-", "+44", "@home", "1969", "A", "'quoted"),
        LabelRecord("A-side", "Don't", "", "", "", "B", "=HYPERLINK(\"x\")"),
    ])
    rows = out.read_text(encoding="utf-8-sig").splitlines()[1:]
    assert rows[0] == "'=1+1;'-;'+44;'@home;1969;A;'quoted"
    assert rows[1] == "A-side;Don't;;;;B;\"'=HYPERLINK(\"\"x\"\")\""


def test_import_removes_only_the_protecting_apostrophe(tmp_path):
    text = (
        "Title;Artist;Label;Country;CatNo\n"
        "'=1+1;'-;'+44;'@home;'quoted\n"
        "''=x;'Til Tuesday;it's;'';'1\n"
    )
    records = read_csv(_write(tmp_path / "in.csv", text)).records
    assert [(r.title, r.artist, r.label, r.country, r.catno) for r in records] == [
        ("=1+1", "-", "+44", "@home", "'quoted"),
        ("'=x", "'Til Tuesday", "it's", "''", "'1"),
    ]

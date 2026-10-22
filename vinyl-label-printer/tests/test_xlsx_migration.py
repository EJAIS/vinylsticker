"""One-time migration of the Print sheet of database.xlsx into labels.db."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

import openpyxl
import pytest

import main
from modules import label_store, xlsx_migration
from modules.excel_reader import read_legacy_workbook
from modules.paths import MigrationResult
from modules.records import LabelRecord

_HEADER = ["Title", "Artist", "Label", "Country", "Year", "Side", "CatNo"]
_PRINT_ROWS = [
    ["Song A", "Artist 1", "Label 1", "UK", 1969, "A", "R 5001"],
    ["Song B", "Artist 1", "Label 1", "UK", 1969, "Side b", None],
    [None, None, None, None, None, None, None],          # blank row: ignored
    ["", "No title", "", "", "", "A", ""],              # no title: ignored
    ["Song C", "Ärtist 2", None, "DE", "1971", "AA", "X-1"],
    ["Song D", "Artist 3", "Label 3", "US", 1980, None, "Y 2"],
]
_EXPECTED = [
    LabelRecord("Song A", "Artist 1", "Label 1", "UK", "1969", "A", "R 5001"),
    LabelRecord("Song B", "Artist 1", "Label 1", "UK", "1969", "B", ""),
    LabelRecord("Song C", "Ärtist 2", "", "DE", "1971", "B", "X-1"),
    LabelRecord("Song D", "Artist 3", "Label 3", "US", "1980", "A", "Y 2"),
]


def _write_xlsx(path: Path, database_rows: int = 2) -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Print"
    ws.append(_HEADER)
    for row in _PRINT_ROWS:
        ws.append(row)
    db = wb.create_sheet("Database")
    db.append(_HEADER)
    for i in range(database_rows):
        db.append([f"Old {i}", "Someone", "", "", 1960, "A", ""])
    wb.save(path)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_rows_equal_the_print_sheet_and_xlsx_is_untouched(data_dir):
    xlsx = data_dir / "database.xlsx"
    _write_xlsx(xlsx)
    digest, mtime = _sha256(xlsx), xlsx.stat().st_mtime_ns

    result = xlsx_migration.migrate_xlsx_queue()

    assert result.status == xlsx_migration.MIGRATED
    assert result.rows == 4
    assert result.database_rows == 2
    queue = label_store.load_queue()
    assert queue == _EXPECTED
    assert queue == read_legacy_workbook(xlsx).print_records
    assert {r.source for r in queue} == {label_store.SOURCE_XLSX}
    marker = json.loads(label_store.get_meta(label_store.META_XLSX_MIGRATED))
    assert marker["rows"] == 4
    assert marker["source"] == str(xlsx)
    assert marker["migrated_at"]

    # Never modified, renamed or deleted
    assert xlsx.is_file()
    assert _sha256(xlsx) == digest
    assert xlsx.stat().st_mtime_ns == mtime
    assert sorted(p.name for p in data_dir.iterdir()) == ["database.xlsx", "labels.db"]


def test_second_run_does_nothing(data_dir):
    _write_xlsx(data_dir / "database.xlsx")
    assert xlsx_migration.migrate_xlsx_queue().status == xlsx_migration.MIGRATED
    marker = label_store.get_meta(label_store.META_XLSX_MIGRATED)
    label_store.replace_queue(label_store.load_queue()[:1])   # user edits the queue

    result = xlsx_migration.migrate_xlsx_queue()

    assert result.status == xlsx_migration.ALREADY_DONE
    assert [r.title for r in label_store.load_queue()] == ["Song A"]
    assert label_store.get_meta(label_store.META_XLSX_MIGRATED) == marker


def test_failure_rolls_back_and_retries(data_dir, monkeypatch):
    _write_xlsx(data_dir / "database.xlsx")
    calls = {"n": 0}
    real_insert = label_store._insert

    def failing_insert(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 3:
            raise OSError("disk full")
        real_insert(*args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(label_store, "_insert", failing_insert)
        result = xlsx_migration.migrate_xlsx_queue()

    assert result.failed
    assert "disk full" in result.error
    assert result.xlsx_path == data_dir / "database.xlsx"
    assert label_store.load_queue() == []                       # rolled back
    assert label_store.get_meta(label_store.META_XLSX_MIGRATED) is None

    # Next start: retried and done
    result = xlsx_migration.migrate_xlsx_queue()
    assert result.status == xlsx_migration.MIGRATED
    assert label_store.load_queue() == _EXPECTED


def test_unreadable_xlsx_fails_and_retries(data_dir):
    xlsx = data_dir / "database.xlsx"
    xlsx.write_bytes(b"not a workbook")

    result = xlsx_migration.migrate_xlsx_queue()
    assert result.failed
    assert label_store.get_meta(label_store.META_XLSX_MIGRATED) is None
    assert xlsx.read_bytes() == b"not a workbook"

    _write_xlsx(xlsx)
    assert xlsx_migration.migrate_xlsx_queue().status == xlsx_migration.MIGRATED


def test_without_xlsx_marker_with_zero_rows(data_dir):
    result = xlsx_migration.migrate_xlsx_queue()

    assert result.status == xlsx_migration.NO_XLSX
    marker = json.loads(label_store.get_meta(label_store.META_XLSX_MIGRATED))
    assert marker["rows"] == 0
    assert marker["source"] is None
    assert label_store.load_queue() == []

    # A database.xlsx dropped into the folder later is not migrated
    _write_xlsx(data_dir / "database.xlsx")
    assert xlsx_migration.migrate_xlsx_queue().status == xlsx_migration.ALREADY_DONE
    assert label_store.load_queue() == []


def test_rows_already_in_the_queue_are_kept(data_dir):
    # e.g. entered after a failed migration, before the successful retry
    label_store.replace_queue([LabelRecord("Mine", "", "", "", "", "A")])
    _write_xlsx(data_dir / "database.xlsx")
    xlsx_migration.migrate_xlsx_queue()
    assert [r.title for r in label_store.load_queue()] == ["Mine"] + [
        r.title for r in _EXPECTED
    ]


@pytest.mark.parametrize(
    ("status", "level", "text"),
    [
        (xlsx_migration.MIGRATED, logging.WARNING, "database.xlsx migrated: 4 rows"),
        (xlsx_migration.NO_XLSX, logging.WARNING, "no file at"),
        (xlsx_migration.FAILED, logging.ERROR, "will retry on next start"),
    ],
)
def test_outcome_is_logged(caplog, data_dir, status, level, text):
    result = xlsx_migration.XlsxMigrationResult(
        status, data_dir / "database.xlsx", rows=4, database_rows=3, error="boom",
    )
    with caplog.at_level(logging.DEBUG, logger="vinyl_label_printer"):
        main._log_data_setup(MigrationResult(already_done=True), result)
    assert any(r.levelno == level and text in r.getMessage() for r in caplog.records)
    database_note = [r for r in caplog.records if "Database sheet has 3 rows" in r.getMessage()]
    assert bool(database_note) == (status == xlsx_migration.MIGRATED)
    if database_note:
        assert "never used by the app" in database_note[0].getMessage()
        assert database_note[0].levelno == logging.WARNING

"""
One-time migration of the print queue from database.xlsx into labels.db.

Versions before 1.1 kept the print queue in the "Print" sheet of database.xlsx
in the data dir. On the first start of 1.1 the rows of that sheet are copied
into labels.db; afterwards the app never reads the workbook again.

  • Runs while the meta marker "xlsx_migrated" is absent from labels.db.
  • The rows (source 'xlsx-migration') and the marker are written in ONE
    transaction: either both exist or neither.
  • database.xlsx is only opened read-only — never modified, renamed or deleted.
  • No database.xlsx: the marker is set with 0 rows, so a workbook that shows
    up later is not migrated.
  • Failure: nothing is written, the marker stays absent and the migration is
    retried on the next start.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from modules import label_store, paths

# Outcomes of migrate_xlsx_queue()
ALREADY_DONE = "already_done"
MIGRATED = "migrated"
NO_XLSX = "no_xlsx"
FAILED = "failed"


@dataclass
class XlsxMigrationResult:
    """Outcome of migrate_xlsx_queue(); logged by main.py."""
    status: str
    xlsx_path: Path | None = None
    rows: int = 0
    # Rows of the never used "Database" sheet (they stay in the xlsx)
    database_rows: int | None = None
    error: str = ""

    @property
    def failed(self) -> bool:
        return self.status == FAILED


def _marker(source: Path | None, rows: int) -> dict[str, str]:
    value = {
        "migrated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": str(source) if source is not None else None,
        "rows": rows,
    }
    return {label_store.META_XLSX_MIGRATED: json.dumps(value)}


def migrate_xlsx_queue() -> XlsxMigrationResult:
    """Copy the Print sheet of database.xlsx into labels.db once. Never raises."""
    xlsx_path: Path | None = None
    try:
        if label_store.get_meta(label_store.META_XLSX_MIGRATED) is not None:
            return XlsxMigrationResult(ALREADY_DONE)

        xlsx_path = paths.get_database_file()
        if not xlsx_path.is_file():
            label_store.append_to_queue([], meta=_marker(None, 0))
            return XlsxMigrationResult(NO_XLSX, xlsx_path)

        # Imported here: openpyxl is only needed for this one-time step
        from modules.excel_reader import read_legacy_workbook

        workbook = read_legacy_workbook(xlsx_path)
        records = workbook.print_records
        label_store.append_to_queue(
            records,
            source=label_store.SOURCE_XLSX,
            meta=_marker(xlsx_path, len(records)),
        )
        return XlsxMigrationResult(
            MIGRATED, xlsx_path, rows=len(records), database_rows=workbook.database_rows,
        )
    except Exception as exc:
        return XlsxMigrationResult(
            FAILED, xlsx_path, error=f"{type(exc).__name__}: {exc}",
        )

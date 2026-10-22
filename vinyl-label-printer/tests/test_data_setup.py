"""Startup data handling: old labels.db files and leftover user files are left alone."""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from pathlib import Path

import main
from modules import label_store, paths
from modules.paths import MigrationResult
from modules.records import LabelRecord

# Version 1 schema exactly as written by the 1.1 pre-releases
_V1_SCHEMA = label_store._MIGRATIONS[0]
_PRE_RELEASE_MARKER = ("xlsx_migrated", '{"rows": 1, "source": null}')


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_pre_release_db(path: Path) -> None:
    conn = sqlite3.connect(str(path))
    try:
        for statement in _V1_SCHEMA:
            conn.execute(statement)
        conn.execute("PRAGMA user_version = 1")
        conn.execute(
            "INSERT INTO print_queue (position, title, artist, side, source, "
            "created_at, updated_at) VALUES (0, 'Old', 'Someone', 'A', "
            "'xlsx-migration', '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00')"
        )
        conn.execute("INSERT INTO meta (key, value) VALUES (?, ?)", _PRE_RELEASE_MARKER)
        conn.commit()
    finally:
        conn.close()


def test_pre_release_db_with_old_marker_opens(data_dir):
    _write_pre_release_db(data_dir / "labels.db")

    queue = label_store.load_queue()
    assert [(r.title, r.source) for r in queue] == [("Old", "xlsx-migration")]

    label_store.replace_queue(queue + [LabelRecord("New", "", "", "", "", "B")])
    assert [r.title for r in label_store.load_queue()] == ["Old", "New"]
    # The marker is ignored, not deleted
    assert label_store.get_meta(_PRE_RELEASE_MARKER[0]) == _PRE_RELEASE_MARKER[1]


def test_spreadsheet_in_data_dir_is_ignored(data_dir):
    leftover = data_dir / "database.xlsx"
    leftover.write_bytes(b"PK\x03\x04 not read by the app")
    digest, mtime = _sha256(leftover), leftover.stat().st_mtime_ns

    assert label_store.load_queue() == []

    assert _sha256(leftover) == digest
    assert leftover.stat().st_mtime_ns == mtime
    assert sorted(p.name for p in data_dir.iterdir()) == ["database.xlsx", "labels.db"]


def test_legacy_migration_copies_settings_and_cache_only(tmp_path, monkeypatch, data_dir):
    legacy = tmp_path / "legacy"
    (legacy / "config").mkdir(parents=True)
    (legacy / "data").mkdir()
    (legacy / "config" / "settings.json").write_text(json.dumps({"language": "en"}))
    (legacy / "config" / "credentials.json").write_text("{}")
    (legacy / "data" / "discogs_cache.db").write_bytes(b"cache")
    leftover = legacy / "data" / "database.xlsx"
    leftover.write_bytes(b"old workbook")
    digest = _sha256(leftover)

    config_dir, cache_dir = tmp_path / "config", tmp_path / "cache"
    config_dir.mkdir()
    cache_dir.mkdir()
    monkeypatch.setattr(paths, "_legacy_dirs", lambda: [legacy])
    monkeypatch.setattr(paths, "get_config_dir", lambda: config_dir)
    monkeypatch.setattr(paths, "get_cache_dir", lambda: cache_dir)

    result = paths.migrate_legacy_data()

    assert not result.errors
    assert sorted(dst.name for _, dst in result.copied) == [
        "credentials.json", "discogs_cache.db", "settings.json",
    ]
    assert (config_dir / paths.MIGRATION_MARKER).is_file()
    assert list(data_dir.iterdir()) == []
    assert _sha256(leftover) == digest


def test_data_setup_is_logged(caplog):
    with caplog.at_level(logging.DEBUG, logger="vinyl_label_printer"):
        main._log_data_setup(MigrationResult(errors=["boom"]))
    assert any(
        r.levelno == logging.ERROR and "boom" in r.getMessage() for r in caplog.records
    )

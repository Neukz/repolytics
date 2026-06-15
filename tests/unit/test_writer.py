"""Tests for repolytics.ingestion.writer."""

import json
from datetime import datetime
from pathlib import Path

import duckdb
import polars as pl

from repolytics.ingestion.writer import partition_path, write_parquet


def test_write_parquet_roundtrips_via_duckdb(
    tmp_path: Path, duckdb_conn: duckdb.DuckDBPyConnection
) -> None:
    records = [
        {"id": 1, "owner": {"login": "a"}, "topics": ["x", "y"]},
        {"id": 2, "owner": {"login": "b"}, "license": None},
    ]
    out = write_parquet(records, tmp_path / "sub" / "repos.parquet")

    assert out.exists()
    rows = duckdb_conn.execute(
        "SELECT data, _loaded_at IS NOT NULL AS has_loaded_at "
        "FROM read_parquet(?) ORDER BY data",
        [str(out)],
    ).fetchall()

    assert len(rows) == 2
    loaded = [json.loads(data) for data, _ in rows]
    assert {record["id"] for record in loaded} == {1, 2}
    assert loaded[0]["owner"]["login"] == "a"  # nested structure preserved
    assert all(has_loaded_at for _, has_loaded_at in rows)


def test_write_parquet_columns(tmp_path: Path) -> None:
    out = write_parquet([{"id": 1}], tmp_path / "x.parquet")
    frame = pl.read_parquet(out)
    assert frame.columns == ["data", "_loaded_at"]


def test_write_parquet_empty_writes_schema_only(tmp_path: Path) -> None:
    out = write_parquet([], tmp_path / "empty.parquet")
    frame = pl.read_parquet(out)
    assert frame.columns == ["data", "_loaded_at"]
    assert frame.height == 0


def test_write_parquet_creates_parent_dirs(tmp_path: Path) -> None:
    out = write_parquet([{"id": 1}], tmp_path / "a" / "b" / "c.parquet")
    assert out.exists()


def test_partition_path_formats_date() -> None:
    on_date = datetime(2024, 1, 2)
    from_datetime = partition_path("data/raw", "github", "commits", on_date)
    assert from_datetime == Path("data/raw/github/commits/2024-01-02.parquet")

    from_string = partition_path("data/raw", "github", "commits", "2024-01-02")
    assert from_string == Path("data/raw/github/commits/2024-01-02.parquet")

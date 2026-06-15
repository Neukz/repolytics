"""Integration tests for repolytics.loading.raw_loader."""

import json
from pathlib import Path

import duckdb
import pytest

from repolytics.ingestion.writer import partition_path, write_parquet
from repolytics.loading.raw_loader import load_raw

FIXTURES = Path(__file__).parent.parent / "fixtures"
REPO = "encode/httpx"
PACKAGE = "polars"
DAY = "2024-01-02"

# Source table -> (fixtures file, metadata).
_GITHUB_TABLES = {
    "commits": "commits.json",
    "issues": "issues.json",
    "pull_requests": "pulls.json",
    "releases": "releases.json",
}


def _read_json(rel: str) -> object:
    return json.loads((FIXTURES / rel).read_text(encoding="utf-8"))


@pytest.fixture
def raw_root(tmp_data_dir: Path) -> Path:
    """A populated `data/raw` tree built from the JSON fixtures via write_parquet."""
    root = tmp_data_dir / "raw"

    repo = _read_json("github_responses/repository.json")
    write_parquet(
        [repo],
        partition_path(root, "github", "repositories", DAY, entity=REPO),
        metadata={"_repo": REPO},
    )
    for table, fname in _GITHUB_TABLES.items():
        write_parquet(
            _read_json(f"github_responses/{fname}"),
            partition_path(root, "github", table, DAY, entity=REPO),
            metadata={"_repo": REPO},
        )
    overall = _read_json("pypi_responses/overall.json")
    write_parquet(
        overall["data"],
        partition_path(root, "pypi", "downloads", DAY, entity=PACKAGE),
        metadata={"_package": PACKAGE},
    )
    return root


def test_load_raw_creates_expected_tables(
    raw_root: Path, duckdb_conn: duckdb.DuckDBPyConnection
) -> None:
    loaded = load_raw(duckdb_conn, raw_root)

    assert set(loaded) == {
        "repositories",
        "commits",
        "issues",
        "pull_requests",
        "releases",
        "downloads",
    }
    schemas = duckdb_conn.execute(
        "SELECT schema_name FROM information_schema.schemata"
    ).fetchall()
    assert "raw" in {row[0] for row in schemas}


def test_load_raw_row_counts(
    raw_root: Path, duckdb_conn: duckdb.DuckDBPyConnection
) -> None:
    load_raw(duckdb_conn, raw_root)

    def count(table: str) -> int:
        return duckdb_conn.execute(f"SELECT count(*) FROM raw.{table}").fetchone()[0]

    assert count("repositories") == 1
    assert count("commits") == 2
    assert count("issues") == 2  # includes the PR-shaped issue (staging filters it)
    assert count("downloads") == 2


def test_load_raw_preserves_data_and_metadata_columns(
    raw_root: Path, duckdb_conn: duckdb.DuckDBPyConnection
) -> None:
    load_raw(duckdb_conn, raw_root)

    columns = duckdb_conn.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = 'raw' AND table_name = 'commits'"
    ).fetchall()
    assert {"data", "_loaded_at", "_repo"} <= {row[0] for row in columns}

    repo = duckdb_conn.execute("SELECT DISTINCT _repo FROM raw.commits").fetchone()[0]
    assert repo == REPO
    package = duckdb_conn.execute(
        "SELECT DISTINCT _package FROM raw.downloads"
    ).fetchone()[0]
    assert package == PACKAGE


def test_load_raw_is_idempotent(
    raw_root: Path, duckdb_conn: duckdb.DuckDBPyConnection
) -> None:
    load_raw(duckdb_conn, raw_root)
    load_raw(duckdb_conn, raw_root)  # second run must not duplicate rows

    count = duckdb_conn.execute("SELECT count(*) FROM raw.commits").fetchone()[0]
    assert count == 2


def test_load_raw_empty_root_returns_nothing(
    tmp_data_dir: Path, duckdb_conn: duckdb.DuckDBPyConnection
) -> None:
    assert load_raw(duckdb_conn, tmp_data_dir / "raw") == []

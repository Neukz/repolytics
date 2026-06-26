"""Integration test: the real sources normalize fixtures into the DuckDB `raw` schema.

Drives the production `github_source` (HTTP mocked) and `pypi_source` (fake BigQuery
runner) from the recorded fixtures via `load_raw_fixtures` into a temporary
DuckDB and asserts the normalized table/column contract that the dbt staging models
depend on.
"""

from collections.abc import Iterator
from pathlib import Path

import duckdb
import pytest

from tests.support.warehouse import PACKAGE, REPO, load_raw_fixtures


@pytest.fixture
def loaded_db(tmp_duckdb_path: Path) -> Iterator[duckdb.DuckDBPyConnection]:
    load_raw_fixtures(tmp_duckdb_path)
    conn = duckdb.connect(str(tmp_duckdb_path))
    try:
        yield conn
    finally:
        conn.close()


def _tables(conn: duckdb.DuckDBPyConnection) -> set[str]:
    rows = conn.execute(
        "select table_name from information_schema.tables where table_schema = 'raw'"
    ).fetchall()
    return {r[0] for r in rows}


def test_normalized_tables_and_child_tables_exist(
    loaded_db: duckdb.DuckDBPyConnection,
) -> None:
    assert {
        "repositories",
        "repositories__topics",
        "commits",
        "commits__parents",
        "issues",
        "issues__labels",
        "pull_requests",
        "pull_requests__labels",
        "releases",
        "downloads",
    } <= _tables(loaded_db)


def test_metadata_columns_present(loaded_db: duckdb.DuckDBPyConnection) -> None:
    commit_cols = {
        r[0]
        for r in loaded_db.execute(
            "select column_name from information_schema.columns "
            "where table_schema = 'raw' and table_name = 'commits'"
        ).fetchall()
    }
    assert {"_repo", "_loaded_at", "commit__author__date"} <= commit_cols

    repo = loaded_db.execute("select distinct _repo from raw.commits").fetchone()[0]
    assert repo == REPO
    package = loaded_db.execute(
        "select distinct _package from raw.downloads"
    ).fetchone()[0]
    assert package == PACKAGE


def test_downloads_contract(loaded_db: duckdb.DuckDBPyConnection) -> None:
    # One non-mirror count per package/day: the columns the staging model reads.
    cols = {
        r[0]
        for r in loaded_db.execute(
            "select column_name from information_schema.columns "
            "where table_schema = 'raw' and table_name = 'downloads'"
        ).fetchall()
    }
    assert {"_package", "date", "downloads", "_loaded_at"} <= cols


def test_pull_request_marker_column_exists(
    loaded_db: duckdb.DuckDBPyConnection,
) -> None:
    # The github source forces `pull_request__url` to exist so the staging PR filter
    # never references a missing column - assert the real source still does so.
    issue_cols = {
        r[0]
        for r in loaded_db.execute(
            "select column_name from information_schema.columns "
            "where table_schema = 'raw' and table_name = 'issues'"
        ).fetchall()
    }
    assert "pull_request__url" in issue_cols


def test_row_counts(loaded_db: duckdb.DuckDBPyConnection) -> None:
    def count(table: str) -> int:
        return loaded_db.execute(f"select count(*) from raw.{table}").fetchone()[0]

    assert count("commits") == 2
    assert count("issues") == 2  # includes the PR-shaped issue (staging filters it)
    assert count("downloads") == 1  # one package, one day from the BigQuery fixture

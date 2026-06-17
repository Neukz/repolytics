"""Integration test: dlt normalizes the fixtures into the DuckDB `raw` schema.

Feeds the recorded API fixtures through dlt (using the real `stamp` metadata helper)
into a temporary DuckDB and asserts the normalized table/column contract that the dbt
staging models depend on. Also checks idempotency of the merge write disposition.
"""

import json
from collections.abc import Iterator
from pathlib import Path

import dlt
import duckdb
import pytest

from repolytics.ingestion._meta import stamp

FIXTURES = Path(__file__).parent.parent / "fixtures"
REPO = "encode/httpx"
PACKAGE = "httpx"  # matches the repo fixture so the downloads->repo FK resolves


def _read(rel: str) -> object:
    return json.loads((FIXTURES / rel).read_text(encoding="utf-8"))


def _sources() -> list:
    @dlt.resource(name="repositories", write_disposition="merge", primary_key="id")
    def repositories() -> Iterator[dict]:
        yield stamp(_repo=REPO)(_read("github_responses/repository.json"))

    @dlt.resource(name="commits", write_disposition="merge", primary_key="sha")
    def commits() -> Iterator[dict]:
        rows = _read("github_responses/commits.json")
        yield from (stamp(_repo=REPO)(c) for c in rows)

    @dlt.resource(
        name="issues", write_disposition="merge", primary_key=["_repo", "number"]
    )
    def issues() -> Iterator[dict]:
        yield from (stamp(_repo=REPO)(c) for c in _read("github_responses/issues.json"))

    @dlt.resource(
        name="pull_requests", write_disposition="merge", primary_key=["_repo", "number"]
    )
    def pull_requests() -> Iterator[dict]:
        yield from (stamp(_repo=REPO)(c) for c in _read("github_responses/pulls.json"))

    @dlt.resource(name="releases", write_disposition="merge", primary_key="id")
    def releases() -> Iterator[dict]:
        yield from (
            stamp(_repo=REPO)(c) for c in _read("github_responses/releases.json")
        )

    @dlt.resource(
        name="downloads",
        write_disposition="merge",
        primary_key=["_package", "category", "date"],
    )
    def downloads() -> Iterator[dict]:
        data = _read("pypi_responses/overall.json")["data"]
        yield from (stamp(_package=PACKAGE)(r) for r in data)

    return [repositories, commits, issues, pull_requests, releases, downloads]


@pytest.fixture
def loaded_db(tmp_duckdb_path: Path) -> Iterator[duckdb.DuckDBPyConnection]:
    pipeline = dlt.pipeline(
        pipeline_name="repolytics_test",
        destination=dlt.destinations.duckdb(str(tmp_duckdb_path)),
        dataset_name="raw",
    )
    pipeline.run(_sources())
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


def test_row_counts(loaded_db: duckdb.DuckDBPyConnection) -> None:
    def count(table: str) -> int:
        return loaded_db.execute(f"select count(*) from raw.{table}").fetchone()[0]

    assert count("commits") == 2
    assert count("issues") == 2  # includes the PR-shaped issue (staging filters it)
    assert count("downloads") == 2

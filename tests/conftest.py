"""Shared pytest fixtures."""

from collections.abc import Iterator
from pathlib import Path

import duckdb
import pytest

from repolytics.config import Settings


@pytest.fixture
def tmp_data_dir(tmp_path: Path) -> Path:
    """A temporary directory standing in for the runtime `data/` tree."""
    data_dir = tmp_path / "data"
    (data_dir / "raw").mkdir(parents=True)
    (data_dir / "warehouse").mkdir(parents=True)
    return data_dir


@pytest.fixture
def tmp_duckdb_path(tmp_data_dir: Path) -> Path:
    """Path to a (not-yet-created) DuckDB file inside the temp data tree."""
    return tmp_data_dir / "warehouse" / "test.duckdb"


@pytest.fixture
def duckdb_conn() -> Iterator[duckdb.DuckDBPyConnection]:
    """An in-memory DuckDB connection, closed on teardown."""
    conn = duckdb.connect(":memory:")
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def settings(tmp_data_dir: Path) -> Settings:
    """A `Settings` instance pointed at the temp data tree."""
    return Settings(
        github_token="test-token",
        github_target_repos="owner/repo-a, owner/repo-b",
        duckdb_path=tmp_data_dir / "warehouse" / "repolytics.duckdb",
        raw_data_path=tmp_data_dir / "raw",
        watermarks_path=tmp_data_dir / "raw" / ".watermarks.json",
    )

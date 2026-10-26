"""Shared pytest fixtures."""

from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def tmp_data_dir(tmp_path_factory) -> Path:
    """A temporary directory standing in for the runtime `data/` tree."""
    tmp_path = tmp_path_factory.mktemp("data")
    data_dir = tmp_path / "data"
    (data_dir / "raw").mkdir(parents=True)
    (data_dir / "warehouse").mkdir(parents=True)
    return data_dir


@pytest.fixture(scope="module")
def tmp_duckdb_path(tmp_data_dir: Path) -> Path:
    """Path to a DuckDB file inside the temp data tree."""
    return tmp_data_dir / "warehouse" / "test.duckdb"

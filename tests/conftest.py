"""Shared pytest fixtures."""

from pathlib import Path

import pytest


@pytest.fixture
def tmp_data_dir(tmp_path: Path) -> Path:
    """A temporary directory standing in for the runtime `data/` tree."""
    data_dir = tmp_path / "data"
    (data_dir / "raw").mkdir(parents=True)
    (data_dir / "warehouse").mkdir(parents=True)
    return data_dir


@pytest.fixture
def tmp_duckdb_path(tmp_data_dir: Path) -> Path:
    """Path to a DuckDB file inside the temp data tree."""
    return tmp_data_dir / "warehouse" / "test.duckdb"

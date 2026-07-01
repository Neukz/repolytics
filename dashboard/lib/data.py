"""Read-only DuckDB access for the dashboard (streamlit-free)."""

from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

from repolytics.config import get_settings


def connect(duckdb_path: str | Path | None = None) -> duckdb.DuckDBPyConnection:
    """Open a read-only DuckDB connection to the warehouse.

    Defaults to `Settings.duckdb_path`.
    """
    path = Path(duckdb_path) if duckdb_path is not None else get_settings().duckdb_path
    return duckdb.connect(str(path), read_only=True)


def run_query(
    conn: duckdb.DuckDBPyConnection, sql: str, params: list | None = None
) -> pd.DataFrame:
    """Execute `sql` with positional `params` and return a pandas DataFrame."""
    return conn.execute(sql, params or []).df()


def has_marts(conn: duckdb.DuckDBPyConnection) -> bool:
    """True when the `marts` schema is populated (so the dashboard has data)."""
    row = conn.execute(
        "select count(*) from information_schema.tables "
        "where table_schema = 'marts' and table_name = 'dim_repositories'"
    ).fetchone()
    return bool(row and row[0])


def date_bounds(conn: duckdb.DuckDBPyConnection) -> tuple[date, date]:
    """Min/max event date across all activity facts, for the sidebar date filter.

    Spans commits, PRs (opened), issues (opened), and releases so the slider covers
    every date-filtered chart - a repo whose PRs/releases extend past its last commit
    is not clipped.
    """
    row = conn.execute(
        """
        with event_keys as (
            select date_key from marts.fct_commits
            union all select opened_date_key from marts.fct_pull_requests
            union all select opened_date_key from marts.fct_issues
            union all select date_key from marts.fct_releases
        )
        select min(d.full_date), max(d.full_date)
        from event_keys e
        join marts.dim_dates d on e.date_key = d.date_key
        """
    ).fetchone()
    return row[0], row[1]

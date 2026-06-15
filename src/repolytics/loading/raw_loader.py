"""Load landed Parquet into the DuckDB `raw` schema."""

from pathlib import Path

import duckdb

from repolytics.config import Settings, get_settings

RAW_SCHEMA = "raw"


def load_raw(conn: duckdb.DuckDBPyConnection, raw_root: str | Path) -> list[str]:
    """Load every `{source}/{table}` partition under `raw_root` into `raw.{table}`.

    Tables are (re)created with `CREATE OR REPLACE`, so the load is idempotent.
    `union_by_name` tolerates partitions written with or without optional
    metadata columns. Returns the sorted list of loaded table names.
    """
    conn.execute(f"CREATE SCHEMA IF NOT EXISTS {RAW_SCHEMA}")
    loaded: list[str] = []
    for table_dir in _table_dirs(Path(raw_root)):
        table = table_dir.name
        pattern = (table_dir / "**" / "*.parquet").as_posix()
        conn.execute(
            f'CREATE OR REPLACE TABLE {RAW_SCHEMA}."{table}" AS '
            "SELECT * FROM read_parquet(?, union_by_name = true)",
            [pattern],
        )
        loaded.append(table)
    return loaded


def _table_dirs(root: Path) -> list[Path]:
    """Return sorted `{source}/{table}` dirs under `root` that hold Parquet."""
    if not root.exists():
        return []
    return sorted(
        table_dir
        for source_dir in root.iterdir()
        if source_dir.is_dir()
        for table_dir in source_dir.iterdir()
        if table_dir.is_dir() and next(table_dir.glob("**/*.parquet"), None)
    )


def load_all(settings: Settings | None = None) -> list[str]:
    """Open the configured DuckDB file and load all raw partitions into it."""
    settings = settings or get_settings()
    settings.duckdb_path.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(settings.duckdb_path))
    try:
        return load_raw(conn, settings.raw_data_path)
    finally:
        conn.close()

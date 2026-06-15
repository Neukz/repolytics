"""Parquet writer for raw API responses.

Lands each record as a single JSON `data` column plus a `_loaded_at` timestamp.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import polars as pl

# Raw-landing schema.
_SCHEMA = {"data": pl.Utf8, "_loaded_at": pl.Datetime(time_unit="us", time_zone="UTC")}


def write_parquet(records: list[dict], path: str | Path) -> Path:
    """Write `records` to `path` as Parquet (JSON `data` column + `_loaded_at`).

    Each record is serialized to a JSON string and stamped with a single batch
    timestamp. An empty `records` list still writes a zero-row file with the
    correct schema, so the partition stays present and schema-stable.
    """
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    loaded_at = datetime.now(UTC)
    frame = pl.DataFrame(
        {
            "data": [json.dumps(record, ensure_ascii=False) for record in records],
            "_loaded_at": [loaded_at] * len(records),
        },
        schema=_SCHEMA,
    )
    frame.write_parquet(out)
    return out


def partition_path(
    root: str | Path, source: str, table: str, date: datetime | str
) -> Path:
    """Build the date-partitioned landing path for a source/table on a date.

    Returns `{root}/{source}/{table}/{YYYY-MM-DD}.parquet`.
    """
    day = date.strftime("%Y-%m-%d") if isinstance(date, datetime) else date
    return Path(root) / source / table / f"{day}.parquet"

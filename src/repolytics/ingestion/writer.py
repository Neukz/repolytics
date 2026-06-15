"""Parquet writer for raw API responses.

Lands each record as a single JSON `data` column plus a `_loaded_at` timestamp.
Optional extraction metadata (e.g. the source repo) is stamped as extra
`_`-prefixed string columns, kept separate from the pristine `data` blob.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import polars as pl

# Raw-landing schema; metadata columns are appended per call.
_SCHEMA = {"data": pl.Utf8, "_loaded_at": pl.Datetime(time_unit="us", time_zone="UTC")}


def write_parquet(
    records: list[dict],
    path: str | Path,
    *,
    metadata: dict[str, str] | None = None,
) -> Path:
    """Write `records` to `path` as Parquet (JSON `data` column + `_loaded_at`).

    Each record is serialized to a JSON string and stamped with a single batch
    timestamp. `metadata` adds one constant string column per key to every row
    (extraction provenance such as the source repo), distinct from the payload.
    An empty `records` list still writes a zero-row file with the full schema,
    so the partition stays present and schema-stable.
    """
    metadata = metadata or {}
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    loaded_at = datetime.now(UTC)
    schema = {**_SCHEMA, **dict.fromkeys(metadata, pl.Utf8)}
    frame = pl.DataFrame(
        {
            "data": [json.dumps(record, ensure_ascii=False) for record in records],
            "_loaded_at": [loaded_at] * len(records),
            **{key: [value] * len(records) for key, value in metadata.items()},
        },
        schema=schema,
    )
    frame.write_parquet(out)
    return out


def partition_path(
    root: str | Path,
    source: str,
    table: str,
    date: datetime | str,
    *,
    entity: str | None = None,
) -> Path:
    """Build the date-partitioned landing path for a source/table on a date.

    When `entity` is given (e.g. a repo or package), it is inserted before
    the date and its `/` slugified to `__`, so each entity lands in its own
    file without collisions.

    Returns `{root}/{source}/{table}/{YYYY-MM-DD}.parquet`.
    """
    day = date.strftime("%Y-%m-%d") if isinstance(date, datetime) else date
    base = Path(root) / source / table
    if entity is not None:
        base = base / entity.replace("/", "__")
    return base / f"{day}.parquet"

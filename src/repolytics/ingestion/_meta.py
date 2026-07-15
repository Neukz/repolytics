"""Shared extraction-metadata stamping for dlt resources.

dlt does not attribute sub-resource rows to their repo or add a load timestamp, so
resources map records through `stamp(...)` to inject `_loaded_at` plus constant
`_`-prefixed provenance columns (`_repo`, `_package`).
"""

from collections.abc import Callable
from datetime import UTC, datetime


def stamp(**metadata: str) -> Callable[[dict], dict]:
    """Build a dlt `add_map` callable that adds a UTC `_loaded_at` and one constant
    column per `metadata` key (e.g. `_repo`/`_package`) to each record.
    """

    def _apply(record: dict) -> dict:
        return {**record, "_loaded_at": datetime.now(UTC), **metadata}

    return _apply

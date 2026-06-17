"""Shared extraction-metadata stamping for dlt resources.

dlt does not attribute sub-resource rows (commits/issues to their repo) or add a
per-row load timestamp by default, so each resource maps its records through
`stamp(...)` to inject `_loaded_at` plus constant `_`-prefixed provenance columns
(`_repo` for GitHub sub-resources, `_package` for PyPI).
"""

from collections.abc import Callable
from datetime import UTC, datetime


def stamp(**metadata: str) -> Callable[[dict], dict]:
    """Build a dlt `add_map` function that stamps `_loaded_at` + `metadata`.

    Returns a callable applied to each record; it adds a UTC `_loaded_at` and one
    constant column per `metadata` key (e.g. `_repo`/`_package`).
    """

    def _apply(record: dict) -> dict:
        return {**record, "_loaded_at": datetime.now(UTC), **metadata}

    return _apply

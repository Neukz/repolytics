"""Shared extraction-metadata stamping for dlt resources.

dlt does not attribute sub-resource rows to their repo or package, so resources
map records through `stamp(...)` to inject constant `_`-prefixed provenance
columns (`_repo`, `_package`). dlt already stamps `_dlt_load_id` on every row and
records `inserted_at` per load in `_dlt_loads`.
"""

from collections.abc import Callable


def stamp(**metadata: str) -> Callable[[dict], dict]:
    """Build a dlt `add_map` callable that adds one constant `_`-prefixed
    provenance column per metadata key (e.g. `_repo`/`_package`) to each record.
    """

    def _apply(record: dict) -> dict:
        return {**record, **metadata}

    return _apply

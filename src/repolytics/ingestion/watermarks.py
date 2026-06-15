"""Watermark store for incremental extraction.

Tracks the last-seen timestamp per `{source}/{endpoint}/{repo}` as a flat JSON
map on disk, so each ingestion run only fetches records newer than last time.
"""

import json
from pathlib import Path


def watermark_key(source: str, endpoint: str, repo: str) -> str:
    """Build the watermark map key for a source/endpoint/repo target."""
    return f"{source}/{endpoint}/{repo}"


def load_watermarks(path: str | Path) -> dict[str, str]:
    """Load the watermark map, returning an empty dict when the file is absent."""
    file = Path(path)
    if not file.exists():
        return {}
    return json.loads(file.read_text(encoding="utf-8"))


def save_watermarks(watermarks: dict[str, str], path: str | Path) -> None:
    """Atomically write the watermark map to `path`, creating parents as needed."""
    file = Path(path)
    file.parent.mkdir(parents=True, exist_ok=True)
    tmp = file.with_name(f"{file.name}.tmp")
    tmp.write_text(json.dumps(watermarks, indent=2), encoding="utf-8")
    tmp.replace(file)

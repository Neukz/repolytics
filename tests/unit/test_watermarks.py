"""Tests for repolytics.ingestion.watermarks."""

from pathlib import Path

from repolytics.ingestion.watermarks import (
    load_watermarks,
    save_watermarks,
    watermark_key,
)


def test_watermark_key_format() -> None:
    key = watermark_key("github", "commits", "encode/httpx")
    assert key == "github/commits/encode/httpx"


def test_load_missing_returns_empty(tmp_path: Path) -> None:
    assert load_watermarks(tmp_path / "nope.json") == {}


def test_save_then_load_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "wm" / ".watermarks.json"
    marks = {"github/commits/encode/httpx": "2024-01-01T00:00:00Z"}
    save_watermarks(marks, path)

    assert path.exists()
    assert load_watermarks(path) == marks


def test_save_creates_parent_dirs(tmp_path: Path) -> None:
    path = tmp_path / "deep" / "nested" / ".watermarks.json"
    save_watermarks({"a": "b"}, path)
    assert path.exists()

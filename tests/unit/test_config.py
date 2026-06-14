"""Tests for repolytics.config.Settings."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from repolytics.config import Settings


def test_loads_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_secret")
    monkeypatch.setenv("GITHUB_TARGET_REPOS", "fastapi/fastapi,pola-rs/polars")
    monkeypatch.setenv("DUCKDB_PATH", "custom/wh.duckdb")

    settings = Settings(_env_file=None)

    assert settings.github_token.get_secret_value() == "ghp_secret"
    assert settings.github_target_repos == "fastapi/fastapi,pola-rs/polars"
    assert settings.duckdb_path == Path("custom/wh.duckdb")


def test_missing_token_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_token_is_not_exposed_in_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_secret")

    settings = Settings(_env_file=None)

    assert "ghp_secret" not in repr(settings)


def test_target_repos_parses_and_strips(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_secret")
    monkeypatch.setenv("GITHUB_TARGET_REPOS", " a/b , c/d ,, e/f ")

    settings = Settings(_env_file=None)

    assert settings.target_repos == ["a/b", "c/d", "e/f"]


def test_target_repos_empty_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_secret")
    monkeypatch.delenv("GITHUB_TARGET_REPOS", raising=False)

    settings = Settings(_env_file=None)

    assert settings.target_repos == []


def test_defaults_apply(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_secret")
    for var in ("DUCKDB_PATH", "RAW_DATA_PATH", "WATERMARKS_PATH"):
        monkeypatch.delenv(var, raising=False)

    settings = Settings(_env_file=None)

    assert settings.duckdb_path == Path("data/warehouse/repolytics.duckdb")
    assert settings.raw_data_path == Path("data/raw")
    assert settings.watermarks_path == Path("data/raw/.watermarks.json")

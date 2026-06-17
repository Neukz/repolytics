"""Unit tests for repolytics.config.Settings."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from repolytics.config import Settings

_PROJECTS_CSV = """\
repo,package
fastapi/fastapi,fastapi
pola-rs/polars,polars
torvalds/linux,
"""


def test_loads_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_secret")
    monkeypatch.setenv("DUCKDB_PATH", "custom/wh.duckdb")

    settings = Settings(_env_file=None)

    assert settings.github_token.get_secret_value() == "ghp_secret"
    assert settings.duckdb_path == Path("custom/wh.duckdb")


def test_missing_token_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_token_is_not_exposed_in_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_secret")

    settings = Settings(_env_file=None)

    assert "ghp_secret" not in repr(settings)


def test_projects_derive_repos_and_packages(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_secret")
    projects_file = tmp_path / "projects.csv"
    projects_file.write_text(_PROJECTS_CSV, encoding="utf-8")

    settings = Settings(_env_file=None, projects_file=projects_file)

    assert settings.target_repos == [
        "fastapi/fastapi",
        "pola-rs/polars",
        "torvalds/linux",
    ]
    # The project with a blank `package` is skipped for PyPI.
    assert settings.packages == ["fastapi", "polars"]


def test_projects_empty_when_file_absent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_secret")

    settings = Settings(_env_file=None, projects_file=tmp_path / "missing.csv")

    assert settings.projects == []
    assert settings.target_repos == []
    assert settings.packages == []


def test_defaults_apply(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_secret")
    monkeypatch.delenv("DUCKDB_PATH", raising=False)

    settings = Settings(_env_file=None)

    assert settings.duckdb_path == Path("data/warehouse/repolytics.duckdb")
    assert settings.projects_file == Path("dbt/seeds/projects.csv")

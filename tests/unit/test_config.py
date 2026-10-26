"""Unit tests for repolytics.config.Settings."""

from pathlib import Path

import pytest

from repolytics.config import Settings

_PROJECTS_CSV = """\
repo,package
fastapi/fastapi,fastapi
pola-rs/polars,polars
torvalds/linux,
"""


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

"""Unit tests for repolytics.ingestion.pipeline helpers and skip paths."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from repolytics.config import Settings
from repolytics.ingestion import pipeline


def test_table_row_counts_filters_dlt_internal_tables() -> None:
    # Fast, isolated test of the filtering logic. A real-pipeline guard lives in
    # tests/integration/test_pipeline.py to catch dlt attribute renames.
    fake = SimpleNamespace(
        last_trace=SimpleNamespace(
            last_normalize_info=SimpleNamespace(
                row_counts={
                    "commits": 2,
                    "issues": 3,
                    "_dlt_loads": 1,
                    "_dlt_pipeline_state": 1,
                }
            )
        )
    )

    assert pipeline._table_row_counts(fake) == {"commits": 2, "issues": 3}


def test_table_row_counts_returns_empty_when_no_normalize_step() -> None:
    # Incremental runs with no new data leave last_normalize_info as None.
    fake_no_trace = SimpleNamespace(last_trace=None)
    fake_no_normalize = SimpleNamespace(
        last_trace=SimpleNamespace(last_normalize_info=None)
    )

    assert pipeline._table_row_counts(fake_no_trace) == {}
    assert pipeline._table_row_counts(fake_no_normalize) == {}


def test_run_github_skips_when_no_repos(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_secret")
    # build_pipeline would hit the network/DuckDB; assert it is never reached.
    monkeypatch.setattr(
        pipeline, "build_pipeline", lambda *_a, **_k: pytest.fail("should not run")
    )
    settings = Settings(_env_file=None, projects_file=tmp_path / "missing.csv")

    assert settings.target_repos == []
    assert pipeline.run_github(settings) == {}


def test_run_pypi_skips_when_no_packages(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_secret")
    monkeypatch.setattr(
        pipeline, "build_pipeline", lambda *_a, **_k: pytest.fail("should not run")
    )
    settings = Settings(_env_file=None, projects_file=tmp_path / "missing.csv")

    assert settings.packages == []
    assert pipeline.run_pypi(settings) == {}

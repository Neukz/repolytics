"""Unit tests for dashboard.lib.health.

The health score is a pure DataFrame -> DataFrame transform, so these tests run
offline with synthetic inputs and assert exact component scores and the final
weighted score.
"""

import numpy as np
import pandas as pd
import pytest

from dashboard.lib.health import (
    REF_STARS,
    TARGET_COMMITS_90D,
    WEIGHTS,
    _log_ratio,
    compute_health,
)


def test_log_ratio_saturates_at_reference() -> None:
    series = pd.Series([TARGET_COMMITS_90D, REF_STARS])
    assert _log_ratio(series, TARGET_COMMITS_90D).iloc[0] == pytest.approx(1.0)
    assert _log_ratio(series, REF_STARS).iloc[1] == pytest.approx(1.0)


def test_log_ratio_zero_is_zero() -> None:
    assert _log_ratio(pd.Series([0]), TARGET_COMMITS_90D).iloc[0] == pytest.approx(0.0)


def test_log_ratio_is_saturating_log() -> None:
    # log1p(value) / log1p(reference), capped at 1.
    assert _log_ratio(pd.Series([9]), TARGET_COMMITS_90D).iloc[0] == pytest.approx(
        np.log1p(9) / np.log1p(TARGET_COMMITS_90D)
    )


def test_compute_health_all_targets_yields_perfect_score() -> None:
    components = pd.DataFrame(
        {
            "repository_name": ["ideal/repo"],
            "commits_90d": [TARGET_COMMITS_90D],
            "pr_merge_rate": [1.0],
            "issue_close_rate": [1.0],
            "days_since_release": [0.0],
            "stars": [REF_STARS],
        }
    )

    scored = compute_health(components)

    assert scored["c_activity"].iloc[0] == pytest.approx(1.0)
    assert scored["c_pr_responsiveness"].iloc[0] == pytest.approx(1.0)
    assert scored["c_issue_management"].iloc[0] == pytest.approx(1.0)
    assert scored["c_release_recency"].iloc[0] == pytest.approx(1.0)
    assert scored["c_popularity"].iloc[0] == pytest.approx(1.0)
    assert scored["health_score"].iloc[0] == pytest.approx(100.0)


def test_compute_health_never_released_yields_zero_release_component() -> None:
    components = pd.DataFrame(
        {
            "repository_name": ["no-releases"],
            "commits_90d": [TARGET_COMMITS_90D],
            "pr_merge_rate": [1.0],
            "issue_close_rate": [1.0],
            "days_since_release": [np.nan],
            "stars": [REF_STARS],
        }
    )

    scored = compute_health(components)

    assert scored["c_release_recency"].iloc[0] == pytest.approx(0.0)


def test_compute_health_all_zeros_yields_zero_score() -> None:
    components = pd.DataFrame(
        {
            "repository_name": ["dead/repo"],
            "commits_90d": [0],
            "pr_merge_rate": [0.0],
            "issue_close_rate": [0.0],
            "days_since_release": [np.nan],
            "stars": [0],
        }
    )

    scored = compute_health(components)

    assert scored["c_activity"].iloc[0] == pytest.approx(0.0)
    assert scored["c_pr_responsiveness"].iloc[0] == pytest.approx(0.0)
    assert scored["c_issue_management"].iloc[0] == pytest.approx(0.0)
    assert scored["c_release_recency"].iloc[0] == pytest.approx(0.0)
    assert scored["c_popularity"].iloc[0] == pytest.approx(0.0)
    assert scored["health_score"].iloc[0] == pytest.approx(0.0)


def test_compute_health_rates_are_clipped_to_unit_interval() -> None:
    components = pd.DataFrame(
        {
            "repository_name": ["clipped/repo"],
            "commits_90d": [0],
            "pr_merge_rate": [2.0],
            "issue_close_rate": [-0.5],
            "days_since_release": [np.nan],
            "stars": [0],
        }
    )

    scored = compute_health(components)

    assert scored["c_pr_responsiveness"].iloc[0] == pytest.approx(1.0)
    assert scored["c_issue_management"].iloc[0] == pytest.approx(0.0)


def test_compute_health_release_recency_half_life() -> None:
    components = pd.DataFrame(
        {
            "repository_name": ["six-months"],
            "commits_90d": [0],
            "pr_merge_rate": [0.0],
            "issue_close_rate": [0.0],
            "days_since_release": [180.0],
            "stars": [0],
        }
    )

    scored = compute_health(components)

    assert scored["c_release_recency"].iloc[0] == pytest.approx(0.5)


def test_compute_health_weighted_score_matches_formula() -> None:
    components = pd.DataFrame(
        {
            "repository_name": ["manual/repo"],
            "commits_90d": [TARGET_COMMITS_90D],  # c_activity = 1.0
            "pr_merge_rate": [0.5],  # c_pr_responsiveness = 0.5
            "issue_close_rate": [0.5],  # c_issue_management = 0.5
            "days_since_release": [180.0],  # c_release_recency = 0.5
            "stars": [0],  # c_popularity = 0.0
        }
    )

    scored = compute_health(components)

    expected = (
        WEIGHTS["activity"] * 1.0
        + WEIGHTS["pr_responsiveness"] * 0.5
        + WEIGHTS["issue_management"] * 0.5
        + WEIGHTS["release_recency"] * 0.5
        + WEIGHTS["popularity"] * 0.0
    ) * 100.0
    assert scored["health_score"].iloc[0] == pytest.approx(expected)


def test_compute_health_does_not_mutate_input() -> None:
    components = pd.DataFrame(
        {
            "repository_name": ["immutable/repo"],
            "commits_90d": [10],
            "pr_merge_rate": [0.5],
            "issue_close_rate": [0.5],
            "days_since_release": [30.0],
            "stars": [1000],
        }
    )
    original = components.copy()

    compute_health(components)

    pd.testing.assert_frame_equal(components, original)


def test_compute_health_preserves_repository_name() -> None:
    components = pd.DataFrame(
        {
            "repository_name": ["keep/me"],
            "commits_90d": [0],
            "pr_merge_rate": [0.0],
            "issue_close_rate": [0.0],
            "days_since_release": [np.nan],
            "stars": [0],
        }
    )

    scored = compute_health(components)

    assert scored["repository_name"].iloc[0] == "keep/me"


def test_compute_health_multi_repo() -> None:
    components = pd.DataFrame(
        {
            "repository_name": ["a", "b"],
            "commits_90d": [0, TARGET_COMMITS_90D],
            "pr_merge_rate": [0.0, 1.0],
            "issue_close_rate": [0.0, 1.0],
            "days_since_release": [np.nan, 0.0],
            "stars": [0, REF_STARS],
        }
    )

    scored = compute_health(components)

    assert scored["health_score"].iloc[0] == pytest.approx(0.0)
    assert scored["health_score"].iloc[1] == pytest.approx(100.0)

"""Composite project-health score (streamlit-free, pure DataFrame -> DataFrame).

A weighted blend of five signals, each scored **absolutely** against a fixed
reference so a project's score is stable regardless of the current selection. Rate
signals (PR merge/issue close) are used directly; unbounded signals (commits, stars)
go through a saturating log transform and release recency through exponential decay.

Input columns come from `queries.health_components`; output adds the five `c_*`
component scores (0..1) and `health_score` (0..100).
"""

import numpy as np
import pandas as pd

WEIGHTS: dict[str, float] = {
    "activity": 0.30,  # commits in the last 90 days
    "pr_responsiveness": 0.20,  # PR merge rate, last 12 months
    "issue_management": 0.20,  # issue close rate, last 12 months
    "release_recency": 0.15,  # how recently the repo last released
    "popularity": 0.15,  # current stars (log-scaled)
}

# Reference targets for the absolute component scores: the value at which a component
# counts as "fully healthy" (or, for release recency, its decay half-life).
TARGET_COMMITS_90D = 90  # ~1 commit/day over the window saturates the activity score
REF_STARS = 50_000  # log-scale reference for "maximally popular"
RELEASE_HALFLIFE_DAYS = 180.0  # released ~6 months ago -> 0.5; never released -> 0


def _log_ratio(series: pd.Series, reference: float) -> pd.Series:
    """Saturating log map to 0..1: `log1p(value) / log1p(reference)`, capped at 1."""
    values = series.astype(float).clip(lower=0)
    return np.minimum(np.log1p(values) / np.log1p(reference), 1.0)


def compute_health(components: pd.DataFrame) -> pd.DataFrame:
    """Return `components` with `c_*` component scores and a 0..100 `health_score`."""
    df = components.copy()

    # Missing release -> infinite days -> recency decays to 0.
    days = df["days_since_release"].astype(float).fillna(np.inf)
    df["c_activity"] = _log_ratio(df["commits_90d"], TARGET_COMMITS_90D)
    df["c_pr_responsiveness"] = df["pr_merge_rate"].astype(float).clip(0, 1)
    df["c_issue_management"] = df["issue_close_rate"].astype(float).clip(0, 1)
    df["c_release_recency"] = 0.5 ** (days / RELEASE_HALFLIFE_DAYS)
    df["c_popularity"] = _log_ratio(df["stars"], REF_STARS)

    df["health_score"] = (
        df["c_activity"] * WEIGHTS["activity"]
        + df["c_pr_responsiveness"] * WEIGHTS["pr_responsiveness"]
        + df["c_issue_management"] * WEIGHTS["issue_management"]
        + df["c_release_recency"] * WEIGHTS["release_recency"]
        + df["c_popularity"] * WEIGHTS["popularity"]
    ) * 100.0
    return df

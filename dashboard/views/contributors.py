"""Contributors & Community page - bus factor, retention, leaderboard."""

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from lib import queries
from views import _components as c


def _bus_factor(commits: np.ndarray) -> int:
    """Min # of top contributors accounting for >=50% of commits."""
    ranked = np.sort(commits)[::-1]
    cutoff = 0.5 * ranked.sum()
    return int(np.searchsorted(np.cumsum(ranked), cutoff) + 1)


def _lorenz(commits: np.ndarray) -> pd.DataFrame:
    """Lorenz points: cumulative commit share held by the bottom x% of contributors."""
    ranked = np.sort(commits)  # ascending -> classic convex Lorenz curve
    k = len(ranked)
    return pd.DataFrame(
        {
            "contributor_frac": np.concatenate([[0.0], np.arange(1, k + 1) / k]),
            "commit_frac": np.concatenate([[0.0], np.cumsum(ranked) / ranked.sum()]),
        }
    )


def render() -> None:
    st.title("👥 Contributors & Community")
    conn = c.get_conn()
    repos, _, _ = c.filters()

    share = queries.commit_share(conn, repos)

    st.subheader("Bus factor")
    st.caption(
        "How many people you'd have to lose before <50% of commit history is covered. "
        "Computed over attributed commits only (commits with no linked GitHub account "
        "are excluded)."
    )
    if not share.empty:
        bf = {
            repo: _bus_factor(g["commits"].to_numpy())
            for repo, g in share.groupby("repository_name")
        }
        cols = st.columns(max(len(bf), 1))
        for col, (repo, value) in zip(cols, bf.items(), strict=False):
            col.metric(repo, value)

        lor = pd.concat(
            _lorenz(g["commits"].to_numpy()).assign(repository_name=repo)
            for repo, g in share.groupby("repository_name")
        )
        equality = pd.DataFrame({"contributor_frac": [0, 1], "commit_frac": [0, 1]})
        curve = (
            alt.Chart(lor)
            .mark_line()
            .encode(
                x=alt.X(
                    "contributor_frac:Q",
                    title="Cumulative share of contributors",
                    axis=alt.Axis(format="%"),
                ),
                y=alt.Y(
                    "commit_frac:Q",
                    title="Cumulative share of commits",
                    axis=alt.Axis(format="%"),
                ),
                color=alt.Color("repository_name:N", title="Repository"),
            )
        )
        line = (
            alt.Chart(equality)
            .mark_line(strokeDash=[4, 4], color="gray")
            .encode(x="contributor_frac:Q", y="commit_frac:Q")
        )
        st.altair_chart(line + curve, width="stretch")

    st.subheader("Contributor leaderboard")
    st.dataframe(
        queries.contributor_leaderboard(conn, repos),
        hide_index=True,
        width="stretch",
    )

    st.subheader("Retention cohorts")
    st.caption(
        "% of each first-active monthly cohort still active N months later. Spans all "
        "tracked projects (activity is aggregated per month, not per repo), so this "
        "view is not affected by the repository filter."
    )
    coh = queries.retention_cohort(conn)
    if not coh.empty:
        coh = coh[coh["months_since"] <= 24].copy()
        recent = sorted(coh["cohort_month"].unique())[-36:]
        coh = coh[coh["cohort_month"].isin(recent)]
        coh["cohort"] = pd.to_datetime(coh["cohort_month"]).dt.strftime("%Y-%m")
        heat = (
            alt.Chart(coh)
            .mark_rect()
            .encode(
                x=alt.X("months_since:O", title="Months since first activity"),
                y=alt.Y("cohort:O", title="Cohort", sort="descending"),
                color=alt.Color(
                    "retention:Q", scale=alt.Scale(scheme="blues"), title="Retention"
                ),
                tooltip=[
                    "cohort",
                    "months_since",
                    alt.Tooltip("retention:Q", format=".0%"),
                    "cohort_size",
                ],
            )
        )
        st.altair_chart(heat, width="stretch")

    st.subheader("Monthly active contributors")
    st.caption(
        "Distinct contributors active each month, split into new (first-ever active "
        "month) vs. returning. Spans all tracked projects (not affected by the "
        "repository filter)."
    )
    acm = queries.active_contributors_monthly(conn)
    c.line_or_fallback(
        acm,
        "month",
        ["new_contributors", "returning_contributors"],
        None,
        "Monthly active contributors",
    )

    st.subheader("Cross-project contributors")
    mp = queries.multi_project_contributors(conn)
    st.caption(
        f"{len(mp)} contributors active in more than one tracked project. Counted "
        "across all tracked projects (not affected by the repository filter)."
    )
    st.dataframe(mp, hide_index=True, width="stretch")

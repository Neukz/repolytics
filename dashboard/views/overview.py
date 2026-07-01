"""Overview page - headline KPIs, current snapshot, and commit activity."""

import streamlit as st

from lib import queries
from views import _components as c


def render() -> None:
    st.title("📊 Overview")
    conn = c.get_conn()
    repos, date_from, date_to = c.filters()

    k = queries.overview_kpis(conn, repos).iloc[0]
    row1 = st.columns(4)
    row1[0].metric("Repositories", int(k.repos))
    row1[1].metric("Commits", f"{int(k.commits):,}")
    row1[2].metric("Contributors", f"{int(k.contributors):,}")
    row1[3].metric("Releases", int(k.releases))

    row2 = st.columns(4)
    row2[0].metric(
        "Pull requests", f"{int(k.prs):,}", f"{k.pr_merge_rate * 100:.0f}% merged"
    )
    row2[1].metric(
        "Issues", f"{int(k.issues):,}", f"{k.issue_close_rate * 100:.0f}% closed"
    )
    row2[2].metric("Stars", f"{int(k.stars):,}")
    row2[3].metric("Forks", f"{int(k.forks):,}")

    st.subheader("Current snapshot")
    st.dataframe(queries.repo_snapshot(conn, repos), hide_index=True, width="stretch")

    st.subheader("Commit activity (per month)")
    cpm = queries.commits_per_month(conn, repos, date_from, date_to)
    c.line_or_fallback(cpm, "month", "commits", "repository_name", "Commit activity")

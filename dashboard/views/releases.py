"""Releases & Cadence page - release timeline and inter-release gaps."""

import altair as alt
import streamlit as st

from lib import queries
from views import _components as c


def render() -> None:
    st.title("🏷️ Releases & Cadence")
    conn = c.get_conn()
    repos, _, _ = c.filters()

    rel = queries.releases(conn, repos)
    if rel.empty:
        st.info("No releases for the current selection.")
        return

    st.subheader("Release timeline")
    timeline = (
        alt.Chart(rel)
        .mark_circle(size=60, opacity=0.6)
        .encode(
            x=alt.X("published_at:T", title="Published"),
            y=alt.Y("repository_name:N", title="Repository"),
            color=alt.Color("repository_name:N", legend=None),
            tooltip=["repository_name", "tag_name", "published_at"],
        )
    )
    st.altair_chart(timeline, width="stretch")

    gaps = queries.release_gaps(conn, repos)
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Median days between releases")
        cadence = gaps.groupby("repository_name", as_index=False)["gap_days"].median()
        st.bar_chart(cadence, x="repository_name", y="gap_days")
    with col2:
        st.subheader("Distribution of release gaps (days)")
        hist = (
            alt.Chart(gaps)
            .mark_bar(opacity=0.7)
            .encode(
                x=alt.X(
                    "gap_days:Q", bin=alt.Bin(maxbins=40), title="Days between releases"
                ),
                y=alt.Y("count()", title="Releases"),
                color=alt.Color("repository_name:N", title="Repository"),
            )
        )
        st.altair_chart(hist, width="stretch")

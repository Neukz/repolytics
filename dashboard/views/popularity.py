"""Popularity & Health page - stars/forks/downloads + composite health score."""

import streamlit as st

from lib import health, queries
from views import _components as c

_COMPONENT_COLS = [
    "repository_name",
    "health_score",
    "c_activity",
    "c_pr_responsiveness",
    "c_issue_management",
    "c_release_recency",
    "c_popularity",
]


def render() -> None:
    st.title("⭐ Popularity & Health")
    conn = c.get_conn()
    repos, _, _ = c.filters()

    st.subheader("Composite health score")
    st.caption(
        "Absolute score (0-100) - each project is scored independently against fixed "
        "reference targets: a weighted blend of recent commit activity (30%), PR merge "
        "rate (20%), issue close rate (20%), release recency (15%), and stars (15%)."
    )
    scored = health.compute_health(queries.health_components(conn, repos))
    st.bar_chart(scored, x="repository_name", y="health_score")
    st.dataframe(scored[_COMPONENT_COLS], hide_index=True, width="stretch")

    st.subheader("Stars over time")
    sf = queries.stars_forks_over_time(conn, repos)
    c.line_or_fallback(sf, "date", "stars", "repository_name", "Stars")

    st.subheader("Forks over time")
    c.line_or_fallback(sf, "date", "forks", "repository_name", "Forks")

    st.subheader("PyPI downloads over time")
    dl = queries.downloads_over_time(conn, repos)
    c.line_or_fallback(dl, "date", "downloads", "package", "Downloads")

    st.subheader("Downloads vs stars")
    dvs = queries.downloads_vs_stars(conn, repos)
    if dvs.empty or dvs["downloads"].sum() == 0:
        st.info("Downloads vs stars fills in once PyPI downloads are backfilled.")
    else:
        st.scatter_chart(dvs, x="downloads", y="stars", color="repository_name")

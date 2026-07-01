"""Development Velocity page - PR/issue throughput and turnaround trends."""

import altair as alt
import streamlit as st

from lib import queries
from views import _components as c


def render() -> None:
    st.title("🚀 Development Velocity")
    conn = c.get_conn()
    repos, date_from, date_to = c.filters()

    st.subheader("PR time-to-merge (median hours, by merge month)")
    st.caption("Lower and falling = a healthier, faster review pipeline.")
    pv = queries.pr_velocity_monthly(conn, repos, date_from, date_to)
    c.line_or_fallback(
        pv, "month", "median_merge_hours", "repository_name", "PR velocity"
    )

    tp = queries.pr_throughput_monthly(conn, repos, date_from, date_to)
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("PRs opened per month")
        c.line_or_fallback(tp, "month", "opened", "repository_name", "PRs opened")
    with col2:
        st.subheader("PR merge rate per month")
        c.line_or_fallback(
            tp, "month", "merge_rate", "repository_name", "PR merge rate"
        )

    ir = queries.issue_resolution_monthly(conn, repos, date_from, date_to)
    col3, col4 = st.columns(2)
    with col3:
        st.subheader("Issue time-to-close (median hours)")
        c.line_or_fallback(
            ir, "month", "median_close_hours", "repository_name", "Issue resolution"
        )
    with col4:
        st.subheader("Issue close rate per month")
        c.line_or_fallback(
            ir, "month", "close_rate", "repository_name", "Issue close rate"
        )

    st.subheader("Issue labels (triage backlog)")
    st.caption("Top labels by issue volume in the selection, split open vs. closed.")
    labels = queries.issue_label_breakdown(conn, repos)
    if labels.empty:
        st.info("No labelled issues for the current selection.")
    else:
        long = labels[["label_name", "open", "closed"]].melt(
            id_vars="label_name",
            value_vars=["open", "closed"],
            var_name="state",
            value_name="issues",
        )
        chart = (
            alt.Chart(long)
            .mark_bar()
            .encode(
                x=alt.X("issues:Q", title="Issues"),
                y=alt.Y("label_name:N", title="Label", sort="-x"),
                color=alt.Color("state:N", title="State"),
                tooltip=["label_name", "state", "issues"],
            )
        )
        st.altair_chart(chart, width="stretch")

"""Shared Streamlit helpers for the view pages (UI layer)."""

from datetime import date

import pandas as pd
import streamlit as st

from lib import data


@st.cache_resource
def get_conn():
    """One cached read-only DuckDB connection, reused across reruns."""
    return data.connect()


def filters() -> tuple[list[str], date | None, date | None]:
    """Current sidebar selection (set in `app.py`)."""
    return (
        st.session_state.get("repos", []),
        st.session_state.get("date_from"),
        st.session_state.get("date_to"),
    )


def line_or_fallback(
    df: pd.DataFrame, x: str, y, color: str | None, label: str
) -> None:
    """Line chart when the series spans >=2 periods; otherwise a graceful note.

    When popularity facts (stars/forks/downloads) hold a single daily snapshot,
    a trend line would be a single point - fall back to showing the current
    values plus a note that the chart fills in as snapshots accrue.
    """
    periods = df[x].nunique() if not df.empty else 0
    if periods >= 2:
        st.line_chart(df, x=x, y=y, color=color)
    elif periods == 1:
        st.info(
            f"{label} has a single snapshot so far - it becomes a trend as runs accrue."
        )
        st.dataframe(df, hide_index=True, width="stretch")
    else:
        st.info(f"No {label.lower()} data for the current selection.")

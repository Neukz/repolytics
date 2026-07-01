"""Repolytics analytics dashboard - Streamlit entrypoint.

Reads the dbt marts read-only from the DuckDB warehouse; defines the global
repo/date filters in the sidebar and renders one page per analytics theme.
"""

import streamlit as st

# Imported relative to the dashboard/ app directory, which Streamlit places on
# sys.path when the app is launched via `streamlit run dashboard/app.py`.
from lib import data, queries
from views import (
    _components as c,
)
from views import (
    contributors,
    overview,
    popularity,
    releases,
    velocity,
)

st.set_page_config(page_title="Repolytics", page_icon="📊", layout="wide")

conn = c.get_conn()

if not data.has_marts(conn):
    st.title("Repolytics")
    st.error("No marts found in the warehouse. Run the pipeline and reload.")
    st.stop()

# ----- Global filters (persist across pages) -----
all_repos = queries.all_repo_names(conn)
st.sidebar.header("Filters")
selected = st.sidebar.multiselect("Repositories", all_repos, default=all_repos)
st.session_state["repos"] = selected or all_repos

low, high = data.date_bounds(conn)
if low and high and low < high:
    date_from, date_to = st.sidebar.slider(
        "Activity date range", min_value=low, max_value=high, value=(low, high)
    )
    st.session_state["date_from"], st.session_state["date_to"] = date_from, date_to

st.sidebar.caption(
    "Reads the dbt marts read-only. The date range filters the activity and velocity "
    "charts; snapshot and all-time views (health, stars/downloads, contributors, "
    "releases) show their full history. Stars/downloads trends fill in as snapshots "
    "accrue."
)

st.navigation(
    [
        st.Page(
            overview.render,
            title="Overview",
            icon="📊",
            url_path="overview",
            default=True,
        ),
        st.Page(
            popularity.render,
            title="Popularity & Health",
            icon="⭐",
            url_path="popularity",
        ),
        st.Page(velocity.render, title="Velocity", icon="🚀", url_path="velocity"),
        st.Page(
            contributors.render,
            title="Contributors",
            icon="👥",
            url_path="contributors",
        ),
        st.Page(releases.render, title="Releases", icon="🏷️", url_path="releases"),
    ]
).run()

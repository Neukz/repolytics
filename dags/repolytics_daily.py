"""Daily Repolytics pipeline: dlt ingestion -> dbt transform.

Ingestion runs as two independent tasks - GitHub and PyPI. Either can fail/retry
without touching the other. Both land into the DuckDB `raw` schema and are
upstream of the dbt transform. Cosmos renders the dbt project; `max_active_tasks=1`
serializes everything so no two tasks open the single-writer DuckDB file at once.
"""

import os
from datetime import timedelta
from pathlib import Path

from airflow.sdk import dag, task
from cosmos import (
    DbtTaskGroup,
    LoadMode,
    ProfileConfig,
    ProjectConfig,
    RenderConfig,
)

# Location of the dbt project inside the container
DBT_PROJECT_DIR = Path(os.environ.get("DBT_PROJECT_DIR", "/opt/airflow/dbt"))

profile_config = ProfileConfig(
    profile_name="repolytics",
    target_name="dev",
    profiles_yml_filepath=DBT_PROJECT_DIR / "profiles.yml",
)


@dag(
    dag_id="repolytics_daily",
    schedule="@daily",
    catchup=False,
    max_active_tasks=1,  # DuckDB is single-writer: never run two dbt tasks at once.
    default_args={"retries": 2, "retry_delay": timedelta(minutes=5)},
    tags=["repolytics", "elt"],
)
def repolytics_daily():
    @task
    def ingest_github() -> None:
        """Run GitHub ingestion into the DuckDB `raw` dataset."""
        from repolytics.ingestion.pipeline import run_github

        run_github()

    @task
    def ingest_pypi() -> None:
        """Run PyPI ingestion into the DuckDB `raw` dataset."""
        from repolytics.ingestion.pipeline import run_pypi

        run_pypi()

    transform = DbtTaskGroup(
        group_id="transform",
        project_config=ProjectConfig(
            dbt_project_path=DBT_PROJECT_DIR,
            # Render the graph from a pre-built manifest.
            manifest_path=DBT_PROJECT_DIR / "target" / "manifest.json",
        ),
        profile_config=profile_config,
        render_config=RenderConfig(
            load_method=LoadMode.DBT_MANIFEST,
            # Detach tests that depend on multiple models into their own
            # tasks scheduled after all parents are built.
            should_detach_multiple_parents_tests=True,
        ),
    )

    [ingest_github(), ingest_pypi()] >> transform


repolytics_daily()

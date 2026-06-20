"""Daily Repolytics pipeline: dlt ingestion -> dbt transform.

Ingestion lands GitHub + PyPI into the DuckDB ``raw`` schema in a single atomic
dlt load. Cosmos renders the dbt project, ``max_active_tasks=1`` serializes everything
so the dbt model tasks never open the single-writer DuckDB file concurrently.
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
    def ingest() -> None:
        """Run the dlt pipeline (GitHub + PyPI) into the DuckDB ``raw`` dataset."""
        from repolytics.ingestion.pipeline import run

        run()

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

    ingest() >> transform


repolytics_daily()

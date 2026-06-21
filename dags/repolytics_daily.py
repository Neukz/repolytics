"""Daily Repolytics pipeline: dlt ingestion -> dbt transform.

Ingestion runs as two independent tasks - GitHub and PyPI. Either can fail/retry
without touching the other. Both land into the DuckDB `raw` schema and are
upstream of the dbt transform. Cosmos renders the dbt project; `max_active_tasks=1`
serializes everything so no two tasks open the single-writer DuckDB file at once.
"""

import logging
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

logger = logging.getLogger(__name__)

# Location of the dbt project inside the container
DBT_PROJECT_DIR = Path(os.environ.get("DBT_PROJECT_DIR", "/opt/airflow/dbt"))


def log_task_failure(context) -> None:
    """Structured failure log for any task (wired via ``default_args``)."""
    ti = context.get("task_instance")
    logger.error(
        "Task failed: dag=%s task=%s run_id=%s try=%s exception=%r",
        getattr(ti, "dag_id", None),
        getattr(ti, "task_id", None),
        context.get("run_id"),
        getattr(ti, "try_number", None),
        context.get("exception"),
    )


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
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "on_failure_callback": log_task_failure,
    },
    tags=["repolytics", "elt"],
)
def repolytics_daily():
    @task(multiple_outputs=False)
    def ingest_github() -> dict[str, int]:
        """Run GitHub ingestion into the DuckDB `raw` dataset.

        Returns per-table row counts (pushed to XCom for the summary task).
        """
        from repolytics.ingestion.pipeline import run_github

        return run_github()

    @task(multiple_outputs=False)
    def ingest_pypi() -> dict[str, int]:
        """Run PyPI ingestion into the DuckDB `raw` dataset.

        Returns per-table row counts (pushed to XCom for the summary task).
        """
        from repolytics.ingestion.pipeline import run_pypi

        return run_pypi()

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

    @task
    def summary(github_counts: dict[str, int], pypi_counts: dict[str, int]) -> None:
        """Log per-source row counts for the run."""
        logger.info(
            "Ingestion summary - GitHub: %s | PyPI: %s",
            github_counts,
            pypi_counts,
        )

    github_counts = ingest_github()
    pypi_counts = ingest_pypi()

    [github_counts, pypi_counts] >> transform >> summary(github_counts, pypi_counts)


repolytics_daily()

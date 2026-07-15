"""Daily Repolytics pipeline: dlt ingestion -> dbt transform.

Ingestion runs as two independent tasks. PyPI is date-windowed: it queries the
BigQuery public dataset for the run's `data_interval_start`, so the DAG is
backfillable per day. GitHub uses dlt incremental cursors (global, not per-interval),
so it is skipped on historical backfill runs. Both land into the DuckDB `raw` schema
upstream of the dbt transform. Cosmos renders the dbt project; `max_active_tasks=1` +
`max_active_runs=1` serialize everything so no two tasks/runs open the single-writer
DuckDB file at once.
"""

import logging
import os
from datetime import UTC, datetime, timedelta
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
    max_active_tasks=1,  # DuckDB is single-writer: never run two dbt tasks at once
    max_active_runs=1,  # serialize runs so a backfill never overlaps DuckDB writers
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
        """Run GitHub incremental ingestion, returning per-table row counts.

        Skipped on historical backfill runs: the dlt cursor is global, so replaying
        old intervals is meaningless.
        """
        from airflow.sdk import get_current_context

        from repolytics.ingestion.pipeline import run_github

        data_interval_end = get_current_context()["data_interval_end"]
        if (datetime.now(UTC) - data_interval_end).days > 1:
            logger.info(
                "Skipping GitHub ingest for backfill interval ending %s",
                data_interval_end,
            )
            return {}
        return run_github()

    @task(multiple_outputs=False)
    def ingest_pypi() -> dict[str, int]:
        """Run PyPI ingestion for the run's `data_interval_start` day."""
        from airflow.sdk import get_current_context

        from repolytics.ingestion.pipeline import run_pypi

        target_date = get_current_context()["data_interval_start"].date()
        return run_pypi(target_date=target_date)

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

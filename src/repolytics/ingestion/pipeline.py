"""dlt pipelines wiring GitHub and PyPI ingestion into the DuckDB `raw` dataset."""

import logging

import dlt

from repolytics.config import Settings, get_settings
from repolytics.ingestion.github_source import github_source
from repolytics.ingestion.pypi_source import pypi_source

logger = logging.getLogger(__name__)


def build_pipeline(settings: Settings) -> dlt.Pipeline:
    """Create the DuckDB-backed dlt pipeline targeting the `raw` dataset."""
    return dlt.pipeline(
        pipeline_name="repolytics",
        destination=dlt.destinations.duckdb(str(settings.duckdb_path)),
        dataset_name="raw",
    )


def _table_row_counts(pipeline: dlt.Pipeline) -> dict[str, int]:
    """Rows loaded per table in the last run, excluding dlt's internal tables.

    Reads `last_trace.last_normalize_info.row_counts` (table name -> count) and
    drops the `_dlt_*` bookkeeping tables so the summary reflects only ingested data.
    """
    counts = pipeline.last_trace.last_normalize_info.row_counts
    return {table: n for table, n in counts.items() if not table.startswith("_dlt")}


def run_github(settings: Settings | None = None) -> dict[str, int]:
    """Run GitHub ingestion into the configured DuckDB warehouse.

    No-ops (logs and returns `{}`) when no repos are configured, so an empty repo
    list succeeds as a skip rather than failing. Returns the per-table row counts
    loaded in this run.
    """
    settings = settings or get_settings()

    repos = settings.target_repos
    if not repos:
        logger.warning("No repos to ingest - check %s", settings.projects_file)
        return {}

    settings.duckdb_path.parent.mkdir(parents=True, exist_ok=True)
    pipeline = build_pipeline(settings)
    source = github_source(repos, settings.github_token.get_secret_value())
    logger.info("GitHub ingestion complete: %s", pipeline.run(source))
    return _table_row_counts(pipeline)


def run_pypi(settings: Settings | None = None) -> dict[str, int]:
    """Run PyPI ingestion into the configured DuckDB warehouse.

    No-ops (logs and returns `{}`) when no packages are configured. Returns the
    per-table row counts loaded in this run.
    """
    settings = settings or get_settings()

    packages = settings.packages
    if not packages:
        logger.warning("No packages to ingest - check %s", settings.projects_file)
        return {}

    settings.duckdb_path.parent.mkdir(parents=True, exist_ok=True)
    pipeline = build_pipeline(settings)
    logger.info("PyPI ingestion complete: %s", pipeline.run(pypi_source(packages)))
    return _table_row_counts(pipeline)


if __name__ == "__main__":
    # Run GitHub + PyPI ingestion (CLI convenience wrapper for both sources).
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    run_github(settings)
    run_pypi(settings)

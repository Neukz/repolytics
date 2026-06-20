"""dlt pipeline wiring GitHub + PyPI ingestion into the DuckDB `raw` dataset."""

import dlt

from repolytics.config import Settings, get_settings
from repolytics.ingestion.github_source import github_source
from repolytics.ingestion.pypi_source import pypi_source


def build_pipeline(settings: Settings) -> dlt.Pipeline:
    """Create the DuckDB-backed dlt pipeline targeting the `raw` dataset."""
    return dlt.pipeline(
        pipeline_name="repolytics",
        destination=dlt.destinations.duckdb(str(settings.duckdb_path)),
        dataset_name="raw",
    )


def run_github(settings: Settings | None = None) -> None:
    """Run GitHub ingestion into the configured DuckDB warehouse.

    No-ops (logs and returns) when no repos are configured, so an empty repo list
    succeeds as a skip rather than failing.
    """
    settings = settings or get_settings()

    repos = settings.target_repos
    if not repos:
        print(f"No repos to ingest - check {settings.projects_file}")
        return

    settings.duckdb_path.parent.mkdir(parents=True, exist_ok=True)
    pipeline = build_pipeline(settings)
    source = github_source(repos, settings.github_token.get_secret_value())
    print(pipeline.run(source))


def run_pypi(settings: Settings | None = None) -> None:
    """Run PyPI ingestion into the configured DuckDB warehouse.

    No-ops (logs and returns) when no packages are configured.
    """
    settings = settings or get_settings()

    packages = settings.packages
    if not packages:
        print(f"No packages to ingest - check {settings.projects_file}")
        return

    settings.duckdb_path.parent.mkdir(parents=True, exist_ok=True)
    pipeline = build_pipeline(settings)
    print(pipeline.run(pypi_source(packages)))


if __name__ == "__main__":
    # Run GitHub + PyPI ingestion (CLI convenience wrapper for both sources).
    settings = get_settings()
    run_github(settings)
    run_pypi(settings)

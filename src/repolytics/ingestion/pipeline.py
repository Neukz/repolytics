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


def run(settings: Settings | None = None) -> None:
    """Run GitHub + PyPI ingestion into the configured DuckDB warehouse."""
    settings = settings or get_settings()

    repos = settings.target_repos
    packages = settings.packages
    if not repos and not packages:
        raise RuntimeError(f"No projects to ingest - check {settings.projects_file}")

    settings.duckdb_path.parent.mkdir(parents=True, exist_ok=True)
    pipeline = build_pipeline(settings)

    # Run both sources in a single load so GitHub + PyPI land atomically.
    sources = []
    if repos:
        sources.append(github_source(repos, settings.github_token.get_secret_value()))
    if packages:
        sources.append(pypi_source(packages))

    info = pipeline.run(sources)
    print(info)


if __name__ == "__main__":
    run()

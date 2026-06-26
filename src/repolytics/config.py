"""Application configuration via Pydantic Settings.

See `.env.example` for the full set of variables.
"""

import csv
from functools import cached_property, lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed configuration loaded from the environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # GitHub
    github_token: SecretStr

    # DuckDB
    duckdb_path: Path = Path("data/warehouse/repolytics.duckdb")

    # Google Cloud project that BigQuery PyPI-download jobs are billed to.
    gcp_project: str | None = None

    # Project list (repo <-> package) - also loaded by dbt as the `projects` seed.
    projects_file: Path = Path("dbt/seeds/projects.csv")

    @cached_property
    def projects(self) -> list[dict[str, str]]:
        """Projects to ingest, each a `{repo, package}` row from `projects_file`.

        `package` may be blank for repos not published to PyPI. Returns an empty
        list when the file is absent.
        """
        if not self.projects_file.exists():
            return []
        with self.projects_file.open(newline="", encoding="utf-8") as file:
            return list(csv.DictReader(file))

    @property
    def target_repos(self) -> list[str]:
        """Target repositories as a clean `owner/name` list."""
        return [p["repo"] for p in self.projects if p.get("repo")]

    @property
    def packages(self) -> list[str]:
        """Target PyPI packages as a clean list (projects without a package skipped)."""
        return [p["package"] for p in self.projects if p.get("package")]


@lru_cache
def get_settings() -> Settings:
    """Return a cached `Settings` instance."""
    return Settings()

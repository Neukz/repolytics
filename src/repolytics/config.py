"""
Application configuration via Pydantic Settings.

See `.env.example` for the full set of variables.
"""

from functools import lru_cache
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
    github_target_repos: str = ""

    # DuckDB
    duckdb_path: Path = Path("data/warehouse/repolytics.duckdb")

    # Paths
    raw_data_path: Path = Path("data/raw")
    watermarks_path: Path = Path("data/raw/.watermarks.json")

    @property
    def target_repos(self) -> list[str]:
        """
        Target repositories as a clean `owner/name` list.

        Parses the comma-separated `GITHUB_TARGET_REPOS` value.
        """
        return [
            repo.strip() for repo in self.github_target_repos.split(",") if repo.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    """Return a cached `Settings` instance."""
    return Settings()

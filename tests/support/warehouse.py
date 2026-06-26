"""Load the recorded API fixtures into a DuckDB `raw` dataset via the real sources.

Run standalone (used by CI to seed a warehouse before `dbt build`):
    DUCKDB_PATH=/tmp/ci.duckdb python -m tests.support.warehouse
"""

import json
import os
from collections.abc import Iterable, Mapping
from datetime import date
from pathlib import Path

import dlt
import responses

from repolytics.ingestion.github_source import github_source
from repolytics.ingestion.pypi_source import pypi_source

FIXTURES = Path(__file__).parent.parent / "fixtures"
REPO = "encode/httpx"
PACKAGE = "httpx"
TARGET_DATE = date(2024, 1, 1)
GITHUB_API = "https://api.github.com"


def _json(rel: str) -> object:
    return json.loads((FIXTURES / rel).read_text(encoding="utf-8"))


def register(rsps: responses.RequestsMock) -> None:
    """Stub every GitHub endpoint the real source hits, one single-page response each.

    No `Link` header is set, so dlt's `RESTClient.paginate` treats each list
    response as a single page and stops. Stubs registered without a query string
    match regardless of the incremental `since`/`sort` params the source adds.
    """
    owner, name = REPO.split("/")
    base = f"{GITHUB_API}/repos/{owner}/{name}"
    rsps.get(base, json=_json("github_responses/repository.json"))
    rsps.get(f"{base}/commits", json=_json("github_responses/commits.json"))
    rsps.get(f"{base}/issues", json=_json("github_responses/issues.json"))
    rsps.get(f"{base}/pulls", json=_json("github_responses/pulls.json"))
    rsps.get(f"{base}/releases", json=_json("github_responses/releases.json"))


def _fake_bq_runner(_sql: str, _parameters: list) -> Iterable[Mapping]:
    """Offline stand-in for the BigQuery client: returns recorded result rows."""
    return _json("pypi_responses/downloads.json")


def load_raw_fixtures(duckdb_path: Path) -> None:
    """Run the real GitHub source (HTTP mocked) + BigQuery PyPI source (fake runner)."""
    pipeline = dlt.pipeline(
        pipeline_name="repolytics_fixtures",
        destination=dlt.destinations.duckdb(str(duckdb_path)),
        dataset_name="raw",
    )
    # assert_all_requests_are_fired=False: dlt may not re-hit every stub on a no-op
    # pass, and we only care that the calls it does make are answered from fixtures.
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        register(rsps)
        pipeline.run(github_source([REPO], token="fixture-token"))
    pipeline.run(pypi_source([PACKAGE], TARGET_DATE, query_runner=_fake_bq_runner))


if __name__ == "__main__":
    path = Path(os.environ["DUCKDB_PATH"])
    path.parent.mkdir(parents=True, exist_ok=True)
    load_raw_fixtures(path)
    print(f"Loaded fixtures into raw dataset at {path}")

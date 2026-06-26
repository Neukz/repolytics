"""Integration test: GitHub incremental cursors bound later runs with `since`.

Runs the real `github_source` (HTTP mocked from fixtures) into a temp DuckDB twice and
inspects the outgoing requests: the first run fetches full history, the second sends a
`since` bound once the cursor has advanced. Repositories stay a full fetch either run.
"""

from pathlib import Path
from urllib.parse import parse_qs, urlparse

import dlt
import responses

from repolytics.ingestion.github_source import github_source
from tests.support.warehouse import REPO, register


def _run(duckdb_path: Path, pipelines_dir: Path) -> None:
    pipeline = dlt.pipeline(
        pipeline_name="gh_incremental_test",
        destination=dlt.destinations.duckdb(str(duckdb_path)),
        dataset_name="raw",
        pipelines_dir=str(pipelines_dir),  # isolate cursor state per test
    )
    pipeline.run(github_source([REPO], token="t"))


def _query_for(rsps: responses.RequestsMock, suffix: str) -> dict:
    url = next(
        c.request.url
        for c in rsps.calls
        if urlparse(c.request.url).path.endswith(suffix)
    )
    return parse_qs(urlparse(url).query)


def _repo_root_called(rsps: responses.RequestsMock) -> bool:
    owner, name = REPO.split("/")
    root = f"/repos/{owner}/{name}"
    return any(urlparse(c.request.url).path.endswith(root) for c in rsps.calls)


def test_incremental_wiring(tmp_duckdb_path: Path, tmp_path: Path) -> None:
    pdir = tmp_path / "dlt"

    # First run: no prior state -> commits fetch full history (no `since`); PRs are
    # sorted by updated desc; repositories are fetched in full.
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        register(rsps)
        _run(tmp_duckdb_path, pdir)
        commits_q = _query_for(rsps, "/commits")
        pulls_q = _query_for(rsps, "/pulls")
        assert _repo_root_called(rsps)

    assert "since" not in commits_q
    assert pulls_q["sort"] == ["updated"]
    assert pulls_q["direction"] == ["desc"]

    # Second run: the commit-date cursor advanced, so `since` now bounds the fetch,
    # and repositories are still fetched in full (not incremental).
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        register(rsps)
        _run(tmp_duckdb_path, pdir)
        commits_q2 = _query_for(rsps, "/commits")
        assert _repo_root_called(rsps)

    assert "since" in commits_q2

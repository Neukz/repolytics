"""dlt source for the GitHub REST API.

One resource per endpoint (repositories, commits, issues, pull requests,
releases), fetched for each target repo.
"""

from collections.abc import Iterator

import dlt
from dlt.sources.helpers.rest_client import RESTClient
from dlt.sources.helpers.rest_client.auth import BearerTokenAuth

from repolytics.ingestion._meta import stamp

BASE_URL = "https://api.github.com"
API_VERSION = "2026-03-10"
PER_PAGE = 100


@dlt.source(name="github")
def github_source(repos: list[str], token: str) -> list:
    """dlt source exposing the GitHub endpoints for each `owner/name` in `repos`."""
    client = RESTClient(
        base_url=BASE_URL,
        auth=BearerTokenAuth(token),
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": API_VERSION,
        },
    )

    def _paginate(path: str, repo: str, params: dict | None = None) -> Iterator[dict]:
        apply = stamp(_repo=repo)
        query = {"per_page": PER_PAGE, **(params or {})}
        for page in client.paginate(path, params=query):
            yield from (apply(item) for item in page)

    @dlt.resource(name="repositories", write_disposition="merge", primary_key="id")
    def repositories() -> Iterator[dict]:
        for repo in repos:
            owner, name = repo.split("/")
            response = client.get(f"/repos/{owner}/{name}")
            response.raise_for_status()
            yield stamp(_repo=repo)(response.json())

    @dlt.resource(name="commits", write_disposition="merge", primary_key="sha")
    def commits(
        updated: dlt.sources.incremental[str] = dlt.sources.incremental(  # noqa: B008
            "commit.author.date"
        ),
    ) -> Iterator[dict]:
        # `since` bounds the fetch server-side on commit date. The cursor is global
        # across repos, so a backdated commit (rebase) pushed today can be missed.
        params = {"since": updated.last_value} if updated.last_value else {}
        for repo in repos:
            owner, name = repo.split("/")
            yield from _paginate(f"/repos/{owner}/{name}/commits", repo, params)

    @dlt.resource(
        name="issues",
        write_disposition="merge",
        primary_key=["_repo", "number"],  # issue number is unique per repo
        # Force the PR marker column to exist so the staging PR filter never
        # references a missing column when a load has no PR-shaped issues.
        columns={"pull_request__url": {"data_type": "text", "nullable": True}},
    )
    def issues(
        updated: dlt.sources.incremental[str] = dlt.sources.incremental(  # noqa: B008
            "updated_at"
        ),
    ) -> Iterator[dict]:
        # `since` filters server-side on updated_at; sort asc so the cursor advances
        # monotonically. Global cursor across repos (see commits caveat).
        params = {"state": "all", "sort": "updated", "direction": "asc"}
        if updated.last_value:
            params["since"] = updated.last_value
        for repo in repos:
            owner, name = repo.split("/")
            yield from _paginate(f"/repos/{owner}/{name}/issues", repo, params)

    @dlt.resource(
        name="pull_requests",
        write_disposition="merge",
        primary_key=["_repo", "number"],  # PR number is unique per repo
    )
    def pull_requests(
        updated: dlt.sources.incremental[str] = dlt.sources.incremental(  # noqa: B008
            "updated_at"
        ),
    ) -> Iterator[dict]:
        # The /pulls endpoint has no `since`; instead we page everything and
        # let dlt's cursor + merge drop/upsert unchanged rows.
        params = {"state": "all", "sort": "updated", "direction": "desc"}
        for repo in repos:
            owner, name = repo.split("/")
            yield from _paginate(f"/repos/{owner}/{name}/pulls", repo, params)

    @dlt.resource(name="releases", write_disposition="merge", primary_key="id")
    def releases() -> Iterator[dict]:
        for repo in repos:
            owner, name = repo.split("/")
            yield from _paginate(f"/repos/{owner}/{name}/releases", repo)

    return [repositories, commits, issues, pull_requests, releases]

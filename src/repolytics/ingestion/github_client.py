"""GitHub REST API client.

Methods return raw JSON exactly as received.
Handles authentication, pagination, rate limiting, and retries with exponential backoff.
"""

import random
import time
from collections.abc import Callable
from datetime import UTC, datetime

import httpx

from repolytics.config import get_settings

# HTTP statuses worth retrying.
RETRYABLE_STATUSES = frozenset({429, 500, 502, 503})


def _to_iso(dt: datetime) -> str:
    """Render a `datetime` as an ISO 8601 UTC string (e.g. `2024-01-01T00:00:00Z`)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


class GitHubClient:
    """Synchronous client for the GitHub REST API.

    Wraps `httpx.Client`. Construct with an explicit token, or use
    `GitHubClient.from_settings()` to read it from the environment. Usable as a
    context manager so the underlying connection pool is closed on exit.
    """

    def __init__(
        self,
        token: str,
        *,
        base_url: str = "https://api.github.com",
        per_page: int = 100,
        max_retries: int = 3,
        backoff_base: float = 1.0,
        rate_limit_threshold: int = 1,
        timeout: httpx.Timeout | None = None,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._per_page = per_page
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._rate_limit_threshold = rate_limit_threshold
        self._sleep = sleep
        self._client = httpx.Client(
            base_url=base_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2026-03-10",
            },
            timeout=timeout
            or httpx.Timeout(connect=30.0, read=60.0, write=60.0, pool=60.0),
            transport=transport,
        )

    @classmethod
    def from_settings(cls, **kwargs: object) -> "GitHubClient":
        """Build a client using the token from `repolytics.config.get_settings()`."""
        token = get_settings().github_token.get_secret_value()
        return cls(token, **kwargs)

    # --- Lifecycle ---

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self._client.close()

    def __enter__(self) -> "GitHubClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # --- Endpoints ---

    def get_repository(self, owner: str, repo: str) -> dict:
        """`GET /repos/{owner}/{repo}` (repository metadata)."""
        return self._request("GET", f"/repos/{owner}/{repo}").json()

    def get_commits(
        self, owner: str, repo: str, since: datetime | None = None
    ) -> list[dict]:
        """`GET /repos/{owner}/{repo}/commits`, optionally since a timestamp."""
        params: dict[str, object] = {"per_page": self._per_page}
        if since is not None:
            params["since"] = _to_iso(since)
        return self._paginate(f"/repos/{owner}/{repo}/commits", params)

    def get_issues(
        self, owner: str, repo: str, since: datetime | None = None
    ) -> list[dict]:
        """`GET /repos/{owner}/{repo}/issues?state=all` (includes PRs upstream)."""
        params: dict[str, object] = {"state": "all", "per_page": self._per_page}
        if since is not None:
            params["since"] = _to_iso(since)
        return self._paginate(f"/repos/{owner}/{repo}/issues", params)

    def get_pull_requests(
        self, owner: str, repo: str, since: datetime | None = None
    ) -> list[dict]:
        """`GET /repos/{owner}/{repo}/pulls?state=all`.

        The pulls endpoint has no `since` parameter, so for incremental pulls
        we sort by `updated` descending and stop paginating once a PR predates
        `since`.
        """
        params: dict[str, object] = {"state": "all", "per_page": self._per_page}
        if since is None:
            return self._paginate(f"/repos/{owner}/{repo}/pulls", params)
        params["sort"] = "updated"
        params["direction"] = "desc"
        return self._paginate(
            f"/repos/{owner}/{repo}/pulls", params, stop=self._stop_before(since)
        )

    def get_releases(self, owner: str, repo: str) -> list[dict]:
        """`GET /repos/{owner}/{repo}/releases`."""
        params: dict[str, object] = {"per_page": self._per_page}
        return self._paginate(f"/repos/{owner}/{repo}/releases", params)

    # --- Internals ---

    def _paginate(
        self,
        url: str,
        params: dict[str, object] | None,
        *,
        stop: Callable[[list[dict]], tuple[list[dict], bool]] | None = None,
    ) -> list[dict]:
        """Follow `Link: rel="next"` pages, collecting all items.

        `stop` filters each page and signals early termination
        (used for the pulls `since` walk).
        """
        results: list[dict] = []
        next_url: str | None = url
        next_params = params
        while next_url is not None:
            response = self._request("GET", next_url, params=next_params)
            page: list[dict] = response.json()
            if stop is not None:
                kept, done = stop(page)
                results.extend(kept)
                if done:
                    break
            else:
                results.extend(page)
            link = response.links.get("next")
            next_url = link["url"] if link else None
            next_params = None  # the next URL already carries the query string
        return results

    def _request(
        self, method: str, url: str, params: dict[str, object] | None = None
    ) -> httpx.Response:
        """Issue one request, retrying transient failures and guarding the limit."""
        response = self._client.request(method, url, params=params)
        for attempt in range(self._max_retries):
            if response.status_code not in RETRYABLE_STATUSES:
                break
            self._sleep(self._retry_delay(response, attempt))
            response = self._client.request(method, url, params=params)
        response.raise_for_status()
        self._guard_rate_limit(response)
        return response

    def _retry_delay(self, response: httpx.Response, attempt: int) -> float:
        """Seconds to wait before a retry: `Retry-After` if present, else backoff."""
        retry_after = response.headers.get("Retry-After")
        if retry_after is not None:
            try:
                return float(retry_after)
            except ValueError:
                pass
        return self._backoff_base * 2**attempt + random.uniform(0, self._backoff_base)

    def _guard_rate_limit(self, response: httpx.Response) -> None:
        """Sleep until the rate-limit window resets when remaining calls run low."""
        remaining = response.headers.get("X-RateLimit-Remaining")
        reset = response.headers.get("X-RateLimit-Reset")
        if remaining is None or reset is None:
            return
        if int(remaining) <= self._rate_limit_threshold:
            delay = float(reset) - time.time()
            if delay > 0:
                self._sleep(delay)

    @staticmethod
    def _stop_before(
        since: datetime,
    ) -> Callable[[list[dict]], tuple[list[dict], bool]]:
        """Build a page filter that keeps PRs updated at/after `since`.

        Assumes pages are sorted by `updated_at` descending, so the first PR
        older than `since` ends the walk.
        """
        cutoff = since if since.tzinfo else since.replace(tzinfo=UTC)

        def stop(page: list[dict]) -> tuple[list[dict], bool]:
            kept: list[dict] = []
            for item in page:
                if datetime.fromisoformat(item["updated_at"]) < cutoff:
                    return kept, True
                kept.append(item)
            return kept, False

        return stop

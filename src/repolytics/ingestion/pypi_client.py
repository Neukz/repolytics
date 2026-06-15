"""PyPI Stats API client.

Methods return raw JSON exactly as received. Handles retries with exponential
backoff and keeps a courtesy delay between requests to stay within PyPI's
informal rate limits.
"""

import time
from collections.abc import Callable

import httpx

from repolytics.ingestion._http import RETRYABLE_STATUSES, retry_delay


class PyPIClient:
    """Synchronous client for the PyPI Stats API.

    Wraps `httpx.Client`. Usable as a context manager so the underlying
    connection pool is closed on exit.
    """

    def __init__(
        self,
        *,
        base_url: str = "https://pypistats.org/api",
        min_interval: float = 1.0,
        max_retries: int = 3,
        backoff_base: float = 1.0,
        timeout: httpx.Timeout | None = None,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._min_interval = min_interval
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._sleep = sleep
        self._client = httpx.Client(
            base_url=base_url,
            headers={"Accept": "application/json"},
            timeout=timeout
            or httpx.Timeout(connect=30.0, read=60.0, write=60.0, pool=60.0),
            transport=transport,
        )

    # --- Lifecycle ---

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self._client.close()

    def __enter__(self) -> "PyPIClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # --- Endpoints ---

    def get_recent_downloads(self, package: str) -> dict:
        """`GET /packages/{package}/recent` (last day/week/month totals)."""
        return self._request("GET", f"/packages/{package}/recent").json()

    def get_overall_downloads(self, package: str, *, mirrors: bool = False) -> dict:
        """`GET /packages/{package}/overall` (daily download time series)."""
        params = {"mirrors": str(mirrors).lower()}
        return self._request(
            "GET", f"/packages/{package}/overall", params=params
        ).json()

    # --- Internals ---

    def _request(
        self, method: str, url: str, params: dict[str, object] | None = None
    ) -> httpx.Response:
        """Issue one request, retrying transient failures, then pause politely."""
        response = self._client.request(method, url, params=params)
        for attempt in range(self._max_retries):
            if response.status_code not in RETRYABLE_STATUSES:
                break
            self._sleep(retry_delay(response, attempt, self._backoff_base))
            response = self._client.request(method, url, params=params)
        response.raise_for_status()
        self._sleep(self._min_interval)
        return response

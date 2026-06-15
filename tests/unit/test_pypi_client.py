"""Tests for repolytics.ingestion.pypi_client.PyPIClient."""

from collections.abc import Callable

import httpx
import pytest

from repolytics.ingestion._http import RETRYABLE_STATUSES
from repolytics.ingestion.pypi_client import PyPIClient
from tests.unit._clients import mock_client


def make_client(
    handler: Callable[[httpx.Request], httpx.Response], **kwargs: object
) -> tuple[PyPIClient, list[float]]:
    """Build a `PyPIClient` over a `MockTransport` with a spy `sleep`."""
    return mock_client(PyPIClient, handler, **kwargs)


def test_get_recent_downloads_returns_raw_json() -> None:
    payload = {
        "data": {"last_day": 1, "last_week": 2, "last_month": 3},
        "package": "polars",
        "type": "recent_downloads",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/packages/polars/recent"
        return httpx.Response(200, json=payload)

    client, _ = make_client(handler, min_interval=0.0)
    assert client.get_recent_downloads("polars") == payload


def test_get_overall_sets_mirrors_param() -> None:
    captured: dict[str, str | None] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["mirrors"] = request.url.params.get("mirrors")
        return httpx.Response(200, json={"data": []})

    client, _ = make_client(handler, min_interval=0.0)
    client.get_overall_downloads("polars", mirrors=True)

    assert captured["path"] == "/api/packages/polars/overall"
    assert captured["mirrors"] == "true"


def test_courtesy_delay_applied() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": {}})

    client, sleeps = make_client(handler, min_interval=1.0)
    client.get_recent_downloads("polars")

    assert sleeps == [1.0]


@pytest.mark.parametrize("status", sorted(RETRYABLE_STATUSES))
def test_retryable_status_retries_then_succeeds(status: int) -> None:
    statuses = [status, 200]
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        current = statuses[len(calls)]
        calls.append(request)
        if current == 200:
            return httpx.Response(200, json={"data": {}})
        return httpx.Response(current)

    client, sleeps = make_client(handler, min_interval=0.0)
    result = client.get_recent_downloads("polars")

    assert result == {"data": {}}
    assert len(calls) == 2
    assert len(sleeps) == 2  # one retry backoff + one courtesy delay


def test_429_honors_retry_after() -> None:
    statuses = [429, 200]
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        status = statuses[len(calls)]
        calls.append(request)
        if status == 429:
            return httpx.Response(429, headers={"Retry-After": "2"})
        return httpx.Response(200, json={"data": {}})

    client, sleeps = make_client(handler, min_interval=0.0)
    result = client.get_recent_downloads("polars")

    assert result == {"data": {}}
    assert sleeps == [2.0, 0.0]  # Retry-After honored, then courtesy delay


def test_context_manager_closes_client() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": {}})

    client, _ = make_client(handler, min_interval=0.0)
    with client as c:
        assert c.get_recent_downloads("polars") == {"data": {}}
    assert client._client.is_closed

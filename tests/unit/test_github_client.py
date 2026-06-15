"""Tests for repolytics.ingestion.github_client.GitHubClient."""

import time
from collections.abc import Callable
from datetime import UTC, datetime

import httpx
import pytest

from repolytics.ingestion._http import RETRYABLE_STATUSES
from repolytics.ingestion.github_client import GitHubClient, _to_iso
from tests.unit._clients import mock_client

# Absolute next-page URL used to drive pagination in tests.
NEXT_URL = "https://api.github.com/x?page=2"
NEXT_LINK = f'<{NEXT_URL}>; rel="next"'


def make_client(
    handler: Callable[[httpx.Request], httpx.Response], **kwargs: object
) -> tuple[GitHubClient, list[float]]:
    """Build a `GitHubClient` over a `MockTransport` with a spy `sleep`."""
    return mock_client(GitHubClient, handler, "test-token", **kwargs)


@pytest.mark.parametrize("dt", [datetime(2024, 1, 1), datetime(2024, 1, 1, tzinfo=UTC)])
def test_to_iso_appends_z(dt: datetime) -> None:
    assert _to_iso(dt) == "2024-01-01T00:00:00Z"


def test_paginates_following_next_link() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(
                200, json=[{"id": 1}, {"id": 2}], headers={"Link": NEXT_LINK}
            )
        return httpx.Response(200, json=[{"id": 3}])

    client, _ = make_client(handler)
    result = client.get_commits("o", "r")

    assert [c["id"] for c in result] == [1, 2, 3]
    assert len(calls) == 2
    assert str(calls[1].url) == NEXT_URL


def test_sleeps_when_rate_limit_low() -> None:
    reset = int(time.time()) + 30

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"id": 1},
            headers={
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset),
            },
        )

    client, sleeps = make_client(handler)
    client.get_repository("o", "r")

    assert len(sleeps) == 1
    assert sleeps[0] > 0


@pytest.mark.parametrize("status", sorted(RETRYABLE_STATUSES))
def test_retryable_status_retries_then_succeeds(status: int) -> None:
    statuses = [status, 200]
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        current = statuses[len(calls)]
        calls.append(request)
        if current == 200:
            return httpx.Response(200, json={"id": 1})
        return httpx.Response(current)

    client, sleeps = make_client(handler)
    result = client.get_repository("o", "r")

    assert result == {"id": 1}
    assert len(calls) == 2  # one failure, one retry
    assert len(sleeps) == 1


def test_raises_after_max_retries() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(502)

    client, sleeps = make_client(handler, max_retries=3)
    with pytest.raises(httpx.HTTPStatusError):
        client.get_repository("o", "r")

    assert len(sleeps) == 3


@pytest.mark.parametrize("status", [400, 401, 403, 404])
def test_non_retryable_status_raises_without_retry(status: int) -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(status)

    client, sleeps = make_client(handler)
    with pytest.raises(httpx.HTTPStatusError):
        client.get_repository("o", "r")

    assert len(calls) == 1
    assert sleeps == []


def test_429_honors_retry_after() -> None:
    statuses = [429, 200]
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        status = statuses[len(calls)]
        calls.append(request)
        if status == 429:
            return httpx.Response(429, headers={"Retry-After": "2"})
        return httpx.Response(200, json={"id": 1})

    client, sleeps = make_client(handler)
    result = client.get_repository("o", "r")

    assert result == {"id": 1}
    assert sleeps == [2.0]


def test_get_repository_returns_raw_json() -> None:
    payload = {
        "id": 123,
        "name": "httpx",
        "owner": {"login": "encode"},
        "stargazers_count": 1000,
        "license": {"spdx_id": "BSD-3-Clause"},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    client, _ = make_client(handler)
    assert client.get_repository("encode", "httpx") == payload


def test_get_commits_passes_since() -> None:
    captured: dict[str, str | None] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["since"] = request.url.params.get("since")
        return httpx.Response(200, json=[])

    client, _ = make_client(handler)
    client.get_commits("o", "r", since=datetime(2024, 1, 1, tzinfo=UTC))

    assert captured["since"] == "2024-01-01T00:00:00Z"


def test_get_issues_sets_state_and_since() -> None:
    captured: dict[str, str | None] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["state"] = request.url.params.get("state")
        captured["since"] = request.url.params.get("since")
        return httpx.Response(200, json=[])

    client, _ = make_client(handler)
    client.get_issues("o", "r", since=datetime(2024, 1, 1, tzinfo=UTC))

    assert captured == {"state": "all", "since": "2024-01-01T00:00:00Z"}


def test_get_releases_returns_list() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[{"tag_name": "v1"}])

    client, _ = make_client(handler)
    assert client.get_releases("o", "r") == [{"tag_name": "v1"}]


def test_get_pull_requests_without_since_fetches_all() -> None:
    captured: dict[str, str | None] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["state"] = request.url.params.get("state")
        captured["sort"] = request.url.params.get("sort")
        return httpx.Response(200, json=[{"number": 1}])

    client, _ = make_client(handler)
    result = client.get_pull_requests("o", "r")

    assert result == [{"number": 1}]
    assert captured["state"] == "all"
    assert captured["sort"] is None


def test_context_manager_closes_client() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id": 1})

    client, _ = make_client(handler)
    with client as c:
        assert c.get_repository("o", "r") == {"id": 1}
    assert client._client.is_closed


def test_from_settings_uses_env_token(monkeypatch: pytest.MonkeyPatch) -> None:
    from repolytics.config import get_settings

    monkeypatch.setenv("GITHUB_TOKEN", "ghp_from_env")
    get_settings.cache_clear()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer ghp_from_env"
        return httpx.Response(200, json={"id": 1})

    client = GitHubClient.from_settings(
        transport=httpx.MockTransport(handler), sleep=lambda _: None
    )
    try:
        assert client.get_repository("o", "r") == {"id": 1}
    finally:
        client.close()
        get_settings.cache_clear()


def test_get_pull_requests_early_exits_past_since() -> None:
    page = [
        {"number": 3, "updated_at": "2024-03-01T00:00:00Z"},
        {"number": 2, "updated_at": "2024-02-01T00:00:00Z"},
        {"number": 1, "updated_at": "2023-12-01T00:00:00Z"},
    ]
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=page, headers={"Link": NEXT_LINK})

    client, _ = make_client(handler)
    result = client.get_pull_requests("o", "r", since=datetime(2024, 1, 1, tzinfo=UTC))

    assert [pr["number"] for pr in result] == [3, 2]
    assert len(calls) == 1  # stopped early, did not follow the next link
    assert calls[0].url.params.get("sort") == "updated"
    assert calls[0].url.params.get("direction") == "desc"

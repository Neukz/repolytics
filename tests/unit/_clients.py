"""Builders for mock-transport-backed API clients."""

from collections.abc import Callable

import httpx


def mock_client(
    client_cls: type,
    handler: Callable[[httpx.Request], httpx.Response],
    *args: object,
    **kwargs: object,
) -> tuple[object, list[float]]:
    """Build an ingestion client over a `MockTransport` with a spy `sleep`.

    Returns the client and the list recording every sleep duration, so tests can
    assert on retry/courtesy waits without blocking.
    """
    sleeps: list[float] = []
    client = client_cls(
        *args,
        transport=httpx.MockTransport(handler),
        sleep=sleeps.append,
        backoff_base=0.0,
        **kwargs,
    )
    return client, sleeps

"""Shared HTTP helpers for the ingestion API clients."""

import random

import httpx

# HTTP statuses worth retrying.
RETRYABLE_STATUSES = frozenset({429, 500, 502, 503})


def retry_delay(response: httpx.Response, attempt: int, backoff_base: float) -> float:
    """Seconds to wait before a retry: `Retry-After` if present, else backoff."""
    retry_after = response.headers.get("Retry-After")
    if retry_after is not None:
        try:
            return float(retry_after)
        except ValueError:
            pass
    return backoff_base * 2**attempt + random.uniform(0, backoff_base)

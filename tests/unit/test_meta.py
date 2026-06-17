"""Unit tests for the repolytics.ingestion._meta.stamp"""

from datetime import datetime

from repolytics.ingestion._meta import stamp


def test_stamp_adds_loaded_at_and_metadata() -> None:
    record = {"id": 1, "name": "x"}
    stamped = stamp(_repo="encode/httpx")(record)

    assert stamped["id"] == 1
    assert stamped["name"] == "x"
    assert stamped["_repo"] == "encode/httpx"
    assert isinstance(stamped["_loaded_at"], datetime)


def test_stamp_does_not_mutate_input() -> None:
    record = {"id": 1}
    stamp(_package="polars")(record)

    assert record == {"id": 1}

"""Unit tests for the BigQuery PyPI source (offline, with a fake query runner)."""

from datetime import date

from repolytics.ingestion import pypi_source as bq


def test_query_is_partition_pruned() -> None:
    # Pruning on the date partition keeps the scan (and cost) tiny.
    assert "DATE(timestamp) = @target_date" in bq.QUERY
    assert "file.project IN UNNEST(@packages)" in bq.QUERY
    assert "NOT IN UNNEST(@mirror_installers)" in bq.QUERY


def test_job_config_caps_bytes_billed() -> None:
    # A cost guard: a mispruned (full-table) query fails instead of running up a bill.
    cfg = bq._job_config(bq._query_parameters(date(2024, 1, 1), ["httpx"]))
    assert cfg.maximum_bytes_billed == bq.MAX_BYTES_BILLED


def test_query_parameters_are_typed() -> None:
    params = bq._query_parameters(date(2024, 1, 1), ["httpx", "polars"])
    by_name = {p.name: p for p in params}

    assert by_name["target_date"].value == date(2024, 1, 1)
    assert by_name["packages"].values == ["httpx", "polars"]
    assert by_name["mirror_installers"].values == bq.MIRROR_INSTALLERS


def test_rows_are_mapped_and_stamped() -> None:
    captured: dict = {}

    def fake_runner(sql: str, parameters: list) -> list[dict]:
        captured["sql"] = sql
        captured["parameters"] = parameters
        return [{"package": "httpx", "downloads": 12000}]

    source = bq.pypi_source(["httpx"], date(2024, 1, 1), query_runner=fake_runner)
    rows = list(source.downloads)

    assert captured["sql"] == bq.QUERY
    assert len(rows) == 1
    row = rows[0]
    assert row["_package"] == "httpx"
    assert row["date"] == "2024-01-01"
    assert row["downloads"] == 12000
    assert "_loaded_at" in row  # stamped provenance

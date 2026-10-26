"""Integration test: pipeline helpers exercised against a real dlt run."""

from pathlib import Path

import dlt

from repolytics.ingestion import pipeline


def test_table_row_counts_against_real_pipeline(tmp_path: Path) -> None:
    """Guard against dlt reshaping the internal attribute chain."""

    @dlt.source(name="tiny")
    def tiny_source() -> list:
        @dlt.resource(name="widgets")
        def widgets():
            yield {"id": 1}
            yield {"id": 2}

        return widgets

    duckdb_path = tmp_path / "real.duckdb"
    real_pipeline = dlt.pipeline(
        pipeline_name="real_counts_test",
        destination=dlt.destinations.duckdb(str(duckdb_path)),
        dataset_name="raw",
    )
    real_pipeline.run(tiny_source())

    assert pipeline._table_row_counts(real_pipeline) == {"widgets": 2}

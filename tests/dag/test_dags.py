"""DAG tests: generic policy checks over every DAG."""

import os
from pathlib import Path

import pytest
from airflow.dag_processing.dagbag import DagBag

REPO_ROOT = Path(__file__).resolve().parents[2]
DAGS_DIR = REPO_ROOT / "dags"
MANIFEST = REPO_ROOT / "dbt" / "target" / "manifest.json"

if not MANIFEST.exists():
    raise RuntimeError(f"dbt manifest not found at {MANIFEST} - run `dbt parse` first.")

# Cosmos reads this at DAG import time; set it before building the bag.
os.environ.setdefault("DBT_PROJECT_DIR", str(REPO_ROOT / "dbt"))

DAG_BAG = DagBag(dag_folder=str(DAGS_DIR), include_examples=False)
ALL_DAGS = list(DAG_BAG.dags.values())
DAG_IDS = [dag.dag_id for dag in ALL_DAGS]


def test_no_import_errors() -> None:
    assert DAG_BAG.import_errors == {}, DAG_BAG.import_errors


@pytest.mark.parametrize("dag", ALL_DAGS, ids=DAG_IDS)
def test_dag_is_tagged(dag) -> None:
    assert dag.tags, f"{dag.dag_id} has no tags"


@pytest.mark.parametrize("dag", ALL_DAGS, ids=DAG_IDS)
def test_dag_retries_at_least_two(dag) -> None:
    retries = dag.default_args.get("retries")
    assert retries is not None and retries >= 2, (
        f"{dag.dag_id} must set retries >= 2 (got {retries!r})"
    )

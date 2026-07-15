"""dlt source for PyPI download stats from the Google BigQuery public dataset.

Queries the day-partitioned `bigquery-public-data.pypi.file_downloads` table for
a single date (partition-pruned, so each run scans only that day), aggregating
non-mirror downloads per package. Date windowing is the increment - re-running a
date is idempotent via `write_disposition="merge"` on `(_package, date)`.
"""

from collections.abc import Callable, Iterable, Iterator, Mapping
from datetime import date

import dlt

from repolytics.ingestion._meta import stamp

TABLE = "bigquery-public-data.pypi.file_downloads"

# Bulk-mirror installers excluded to match pypistats' "without_mirrors" definition.
# See: https://pypistats.org/faqs#what-is-the-difference-between-without_mirrors-and-with_mirrors
MIRROR_INSTALLERS = ["bandersnatch", "z3c.pypimirror", "Artifactory", "devpi"]

# Cost guard: a pruned single-day query stays well under this, so hitting it means
# the date filter was lost.
MAX_BYTES_BILLED = 100 * 1024**3  # 100 GiB

QUERY = f"""
SELECT file.project AS package, COUNT(*) AS downloads
FROM `{TABLE}`
WHERE DATE(timestamp) = @target_date
  AND file.project IN UNNEST(@packages)
  AND COALESCE(details.installer.name, '') NOT IN UNNEST(@mirror_installers)
GROUP BY file.project
"""

# (sql, query_parameters) -> rows, each row mapping `package` and `downloads`.
QueryRunner = Callable[[str, list], Iterable[Mapping]]


def _query_parameters(target_date: date, packages: list[str]) -> list:
    """Build the BigQuery query parameters."""
    from google.cloud import bigquery

    return [
        bigquery.ScalarQueryParameter("target_date", "DATE", target_date),
        bigquery.ArrayQueryParameter("packages", "STRING", packages),
        bigquery.ArrayQueryParameter("mirror_installers", "STRING", MIRROR_INSTALLERS),
    ]


def _job_config(parameters: list) -> object:
    """Query config binding the parameters and capping bytes billed."""
    from google.cloud import bigquery

    return bigquery.QueryJobConfig(
        query_parameters=parameters,
        maximum_bytes_billed=MAX_BYTES_BILLED,
    )


def _default_runner(project: str | None) -> QueryRunner:
    """Run the query against BigQuery, billing jobs to `project`."""

    def run(sql: str, parameters: list) -> Iterable[Mapping]:
        from google.cloud import bigquery

        client = bigquery.Client(project=project)
        return client.query(sql, job_config=_job_config(parameters)).result()

    return run


@dlt.source(name="pypi")
def pypi_source(
    packages: list[str],
    target_date: date,
    *,
    project: str | None = None,
    query_runner: QueryRunner | None = None,
) -> object:
    """dlt source yielding one daily non-mirror download count per package.

    `target_date` selects the BigQuery day partition. `query_runner` is injectable
    for offline tests; by default it runs against BigQuery using `project` for billing.
    """
    runner = query_runner or _default_runner(project)

    @dlt.resource(
        name="downloads",
        write_disposition="merge",
        primary_key=["_package", "date"],
    )
    def downloads() -> Iterator[dict]:
        apply = stamp()  # adds _loaded_at only; package is a real column
        iso = target_date.isoformat()
        for row in runner(QUERY, _query_parameters(target_date, packages)):
            yield apply(
                {
                    "_package": row["package"],
                    "date": iso,
                    "downloads": row["downloads"],
                }
            )

    return downloads

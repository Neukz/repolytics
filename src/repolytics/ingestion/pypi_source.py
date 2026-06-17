"""dlt source for the PyPI Stats API.

Fetches the per-package overall download time series and yields one row per
day/category, stamped with `_package` + `_loaded_at`.
"""

import time
from collections.abc import Iterator

import dlt
from dlt.sources.helpers.rest_client import RESTClient

from repolytics.ingestion._meta import stamp

BASE_URL = "https://pypistats.org/api"


@dlt.source(name="pypi")
def pypi_source(packages: list[str], *, min_interval: float = 1.0) -> object:
    """dlt source yielding PyPI overall downloads for each package."""
    client = RESTClient(base_url=BASE_URL)

    @dlt.resource(
        name="downloads",
        write_disposition="merge",
        primary_key=["_package", "category", "date"],
    )
    def downloads() -> Iterator[dict]:
        for package in packages:
            response = client.get(f"/packages/{package}/overall")
            response.raise_for_status()
            apply = stamp(_package=package)
            yield from (apply(row) for row in response.json()["data"])
            time.sleep(min_interval)  # courtesy delay between packages

    return downloads

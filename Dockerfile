# Custom Airflow image: extends the official image with Cosmos + dbt, installed
# from uv.lock so the runtime matches the local .venv.

FROM apache/airflow:3.2.2-python3.13

COPY --from=ghcr.io/astral-sh/uv:0.11.23 /uv /uvx /bin/

ENV UV_LINK_MODE=copy

# Install as root: the system site-packages (/usr/python) is root-owned
USER root

# Resolve the orchestration + dbt groups from the lockfile and install them into
# the image's system Python. --no-emit-package apache-airflow excludes the meta
# package so the base image's Airflow is left untouched.
COPY pyproject.toml uv.lock /tmp/build/
RUN uv export --frozen --no-emit-project --no-hashes \
      --directory /tmp/build \
      --no-emit-package apache-airflow \
      --group orchestration --group dbt \
    | uv pip install --system --no-cache -r - \
 && rm -rf /tmp/build

# Install the repolytics package, --no-deps because deps already installed above.
COPY --chown=airflow:0 pyproject.toml uv.lock README.md /opt/airflow/project/
COPY --chown=airflow:0 src /opt/airflow/project/src
RUN uv pip install --system --no-cache --no-deps -e /opt/airflow/project

USER airflow

-- PyPI daily download fact: one row per package per day. `repository_key` is resolved
-- through the `projects` seed (package -> repo) and the SCD2 dim_repositories half-open
-- range; it is nullable for packages with no mapped/ingested repo.
-- Filtered to the 'without_mirrors' overall time-series category to avoid double
-- counting 'with_mirrors' and to exclude the recent-endpoint 'last_*' aggregates.
-- Incremental (delete+insert on download_key): only processes days at or after the
-- latest download_date already loaded; the unique key keeps it idempotent.

{{
    config(
        materialized='incremental',
        unique_key='download_key',
        incremental_strategy='delete+insert',
        on_schema_change='fail',
    )
}}

with downloads as (
    select * from {{ ref('stg_pypi__downloads') }}
    where category = 'without_mirrors'
    {% if is_incremental() %}
    -- date_key is the only date column on the target table; compare the day's key.
    and {{ date_key('download_date') }} >= (select max(date_key) from {{ this }})
    {% endif %}
)

select
    {{ dbt_utils.generate_surrogate_key(['d.package', 'd.download_date']) }}
        as download_key,
    d.package,
    r.repository_key,
    {{ date_key('d.download_date') }} as date_key,
    d.download_count
from downloads d
left join {{ ref('projects') }} p on d.package = p.package
{{ scd2_repository_join('p.repo', 'd.download_date') }}

-- PyPI daily download fact: one row per package per day.
-- Filtered to the 'without_mirrors' overall time-series category to avoid double
-- counting 'with_mirrors' and to exclude the recent-endpoint 'last_*' aggregates.
-- Incremental (delete+insert on download_key): only processes days at or after the
-- latest download_date already loaded; the unique key keeps it idempotent.

{{
    config(
        materialized='incremental',
        unique_key='download_key',
        incremental_strategy='delete+insert',
        on_schema_change='sync_all_columns',
    )
}}

with downloads as (
    select * from {{ ref('stg_pypi__downloads') }}
    where category = 'without_mirrors'
    {% if is_incremental() %}
    -- date_key is the only date column on the target table; compare the day's key.
    and cast(strftime(download_date, '%Y%m%d') as integer)
        >= (select max(date_key) from {{ this }})
    {% endif %}
)

select
    {{ dbt_utils.generate_surrogate_key(['package', 'download_date']) }} as download_key,
    package,
    cast(strftime(download_date, '%Y%m%d') as integer) as date_key,
    download_count
from downloads

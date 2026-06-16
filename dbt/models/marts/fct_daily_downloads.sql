-- PyPI daily download fact: one row per package per day.
-- Filtered to the 'without_mirrors' overall time-series category to avoid double
-- counting 'with_mirrors' and to exclude the recent-endpoint 'last_*' aggregates.

with downloads as (
    select * from {{ ref('stg_pypi__downloads') }}
    where category = 'without_mirrors'
)

select
    {{ dbt_utils.generate_surrogate_key(['package', 'download_date']) }} as download_key,
    package,
    cast(strftime(download_date, '%Y%m%d') as integer) as date_key,
    download_count
from downloads

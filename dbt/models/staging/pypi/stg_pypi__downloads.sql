-- Structural cleaning over dlt's normalized `downloads` table.

with downloads as (
    select * from {{ source('pypi', 'downloads') }}
)

select
    _package as package,
    category,
    date::date as download_date,
    downloads as download_count,
    _loaded_at
from downloads

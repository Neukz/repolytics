with source as (
    select data::json as d, _package, _loaded_at
    from {{ source('pypi', 'downloads') }}
)

select
    _package as package,
    d ->> '$.category' as category,
    (d ->> '$.date')::date as download_date,
    (d ->> '$.downloads')::bigint as download_count,
    _loaded_at
from source

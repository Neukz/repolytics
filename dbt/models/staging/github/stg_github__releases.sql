with source as (
    select data::json as d, _repo, _loaded_at
    from {{ source('github', 'releases') }}
)

select
    (d ->> '$.id')::bigint as release_id,
    _repo as repository,
    d ->> '$.tag_name' as tag_name,
    d ->> '$.name' as name,
    (d ->> '$.published_at')::timestamp as published_at,
    _loaded_at
from source

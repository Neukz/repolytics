-- Structural cleaning over dlt's normalized `releases` table.

with releases as (
    select * from {{ source('github', 'releases') }}
)

select
    id as release_id,
    _repo as repository,
    tag_name,
    name,
    published_at,
    _loaded_at
from releases

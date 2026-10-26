-- Release activity fact: one row per published release, resolving repository via the
-- SCD2 join on the publish date. No additive measure - analyze by counting (cadence).

{{
    config(
        materialized='table',
    )
}}

with releases as (
    select * from {{ ref('stg_github__releases') }}
    -- Drafts have no publish date; exclude them so date_key / repository_key resolve.
    where published_at is not null
)

select
    {{ dbt_utils.generate_surrogate_key(['rel.repository', 'rel.release_id']) }}
        as release_key,
    r.repository_key,
    {{ date_key('rel.published_at') }} as date_key,
    rel.tag_name,
    rel.name as release_name,
    rel.published_at
from releases rel
{{ scd2_repository_join('rel.repository', 'rel.published_at::date') }}

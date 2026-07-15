-- Release activity fact: one row per published release, resolving repository via the
-- SCD2 join on the publish date. No additive measure - analyze by counting (cadence).
-- Incremental on the monotonic dlt `_loaded_at` (publish dates can be backdated).

{{
    config(
        materialized='incremental',
        unique_key='release_key',
        incremental_strategy='delete+insert',
        on_schema_change='fail',
    )
}}

with releases as (
    select * from {{ ref('stg_github__releases') }}
    -- Drafts have no publish date; exclude them so date_key / repository_key resolve.
    where published_at is not null
    {% if is_incremental() %}
    and _loaded_at >= (select max(_loaded_at) from {{ this }})
    {% endif %}
)

select
    {{ dbt_utils.generate_surrogate_key(['rel.repository', 'rel.release_id']) }}
        as release_key,
    r.repository_key,
    {{ date_key('rel.published_at') }} as date_key,
    rel.tag_name,
    rel.name as release_name,
    rel.published_at,
    rel._loaded_at
from releases rel
{{ scd2_repository_join('rel.repository', 'rel.published_at::date') }}

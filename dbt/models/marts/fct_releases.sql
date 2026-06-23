-- Release activity fact: one row per published release. Joins to dim_repositories via
-- the SCD2 half-open date range (event_date >= valid_from AND < valid_to) so each
-- release maps to the repository version current when it was published; to dim_dates
-- via an inline YYYYMMDD key on the publish date. An event fact with no additive
-- measure - analyze by counting (release cadence, time between releases).
-- Incremental (delete+insert on release_key) keyed on the monotonic dlt `_loaded_at`
-- (publish dates can be backdated); the unique key keeps it idempotent.

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

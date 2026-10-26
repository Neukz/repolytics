-- Periodic-snapshot fact: one row per repository per capture day, recording the
-- volatile stars/forks/open_issues. GitHub returns only current values (no history),
-- so each daily run appends that day's snapshot.

{{
    config(
        materialized='table',
    )
}}

with repositories as (
    select
        r.*,
        cast(dl.inserted_at as date) as capture_date
    from {{ ref('stg_github__repositories') }} r
    join {{ source('github', '_dlt_loads') }} dl
        on r._dlt_load_id = dl.load_id
)

select
    {{ dbt_utils.generate_surrogate_key(['m.repository_id', 'm.capture_date']) }}
        as metric_key,
    m.repository_id,
    m.repository_name,
    r.repository_key,
    {{ date_key('m.capture_date') }} as date_key,
    m.stars,
    m.forks,
    m.open_issues
from repositories m
{{ scd2_repository_join('m.repository_name', 'm.capture_date') }}

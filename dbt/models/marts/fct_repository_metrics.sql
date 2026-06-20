-- GitHub repository metrics fact: a periodic-snapshot fact at one row per repository
-- per capture (ingestion) day, recording the volatile counters stars/forks/open_issues.
-- GitHub's API returns only the *current* counter values (no history), so history is
-- accumulated incrementally - each daily run appends that day's values, dated by the
-- dlt load timestamp. `repository_key` resolves through the SCD2 dim_repositories
-- half-open range for the capture date. Incremental (delete+insert on metric_key)
-- keeps same-day re-runs idempotent.

{{
    config(
        materialized='incremental',
        unique_key='metric_key',
        incremental_strategy='delete+insert',
        on_schema_change='sync_all_columns',
    )
}}

with repositories as (
    select
        *,
        cast(_loaded_at as date) as capture_date
    from {{ ref('stg_github__repositories') }}
    {% if is_incremental() %}
    -- Only (re)load capture days at or after the latest already loaded.
    where {{ date_key('_loaded_at') }} >= (select max(date_key) from {{ this }})
    {% endif %}
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

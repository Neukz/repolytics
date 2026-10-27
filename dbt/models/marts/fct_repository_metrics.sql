-- Periodic-snapshot fact: one row per repository per capture day, recording the
-- volatile stars/forks/open_issues. GitHub returns only current values (no history),
-- so each daily run appends that day's snapshot. `is_latest` flags the most recent
-- capture per repository, so consumers don't re-derive it with a window function.

with repositories as (
    select
        r.*,
        cast(dl.inserted_at as date) as capture_date
    from {{ ref('stg_github__repositories') }} r
    join {{ source('github', '_dlt_loads') }} dl
        on r._dlt_load_id = dl.load_id
),

resolved as (
    select
        {{ dbt_utils.generate_surrogate_key(['m.repository_id', 'm.capture_date']) }}
            as metric_key,
        m.repository_id,
        m.repository_name,
        r.repository_key,
        m.capture_date,
        m.stars,
        m.forks,
        m.open_issues
    from repositories m
    {{ scd2_repository_join('m.repository_name', 'm.capture_date') }}
)

select
    metric_key,
    repository_id,
    repository_name,
    repository_key,
    {{ date_key('capture_date') }} as date_key,
    stars,
    forks,
    open_issues,
    -- Partitioned on the immutable ID so a rename can't split a repository's history.
    row_number() over (
        partition by repository_id order by capture_date desc
    ) = 1 as is_latest
from resolved

-- Commit activity fact: one row per commit. Joins to dim_repositories via the SCD2
-- half-open date range (event_date >= valid_from AND < valid_to) so each commit maps
-- to the repository version that was current when it landed; to dim_contributors on
-- author login; and to dim_dates via an inline YYYYMMDD key.
-- Incremental (delete+insert on commit_key): each run only processes rows loaded
-- since the last run, keyed on the monotonic dlt `_loaded_at` (the git author date is
-- not monotonic, so a rebased/old-authored commit pushed today would be skipped).
-- The unique key keeps it idempotent.

{{
    config(
        materialized='incremental',
        unique_key='commit_key',
        incremental_strategy='delete+insert',
        on_schema_change='sync_all_columns',
    )
}}

with commits as (
    select * from {{ ref('stg_github__commits') }}
    {% if is_incremental() %}
    where _loaded_at >= (select max(_loaded_at) from {{ this }})
    {% endif %}
)

select
    {{ dbt_utils.generate_surrogate_key(['c.repository', 'c.commit_sha']) }} as commit_key,
    r.repository_key,
    co.contributor_key,
    {{ date_key('c.committed_at') }} as date_key,
    c.commit_sha as commit_hash,
    c.committed_at,
    c._loaded_at
from commits c
{{ scd2_repository_join('c.repository', 'c.committed_at::date') }}
left join {{ ref('dim_contributors') }} co
    on c.author_login = co.username

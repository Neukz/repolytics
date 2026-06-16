-- Commit activity fact: one row per commit. Joins to dim_repositories via the SCD2
-- half-open date range (event_date >= valid_from AND < valid_to) so each commit maps
-- to the repository version that was current when it landed; to dim_contributors on
-- author login; and to dim_dates via an inline YYYYMMDD key.
-- Incremental (delete+insert on commit_key): each run only processes commits at or
-- after the latest committed_at already loaded; the unique key keeps it idempotent.

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
    where committed_at >= (select max(committed_at) from {{ this }})
    {% endif %}
)

select
    {{ dbt_utils.generate_surrogate_key(['c.repository', 'c.commit_sha']) }} as commit_key,
    r.repository_key,
    co.contributor_key,
    cast(strftime(c.committed_at, '%Y%m%d') as integer) as date_key,
    c.commit_sha as commit_hash,
    c.additions as lines_added,
    c.deletions as lines_deleted,
    c.committed_at
from commits c
left join {{ ref('dim_repositories') }} r
    on c.repository = r.repository_name
    and c.committed_at::date >= r.valid_from
    and c.committed_at::date < r.valid_to
left join {{ ref('dim_contributors') }} co
    on c.author_login = co.username

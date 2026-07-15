-- Commit activity fact: one row per commit, resolving repository via the SCD2 join.
-- Incremental on the dlt `_loaded_at` because the git author date isn't monotonic.

{{
    config(
        materialized='incremental',
        unique_key='commit_key',
        incremental_strategy='delete+insert',
        on_schema_change='fail',
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

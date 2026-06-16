-- Issue lifecycle fact: one row per issue. Repository resolved via the SCD2 half-open
-- range on the issue open date; author via dim_contributors; opened/closed date keys
-- are inline YYYYMMDD references to dim_dates (closed is nullable).

with issues as (
    select * from {{ ref('stg_github__issues') }}
)

select
    {{ dbt_utils.generate_surrogate_key(['i.repository', 'i.issue_number']) }} as issue_key,
    r.repository_key,
    co.contributor_key as author_key,
    cast(strftime(i.created_at, '%Y%m%d') as integer) as opened_date_key,
    cast(strftime(i.closed_at, '%Y%m%d') as integer) as closed_date_key,
    i.is_closed,
    i.time_to_close_hours,
    i.comment_count
from issues i
left join {{ ref('dim_repositories') }} r
    on i.repository = r.repository_name
    and i.created_at::date >= r.valid_from
    and i.created_at::date < r.valid_to
left join {{ ref('dim_contributors') }} co
    on i.author_login = co.username

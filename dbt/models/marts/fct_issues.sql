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
    {{ date_key('i.created_at') }} as opened_date_key,
    {{ date_key('i.closed_at') }} as closed_date_key,
    i.state = 'closed' as is_closed,
    case
        when i.closed_at is not null
            then datediff('hour', i.created_at, i.closed_at)
    end as time_to_close_hours,
    i.comment_count
from issues i
{{ scd2_repository_join('i.repository', 'i.created_at::date') }}
left join {{ ref('dim_contributors') }} co
    on i.author_login = co.username

-- Pull request lifecycle fact: one row per PR, resolving repository via the SCD2 join
-- on the open date (merged_date_key is nullable for unmerged PRs).

with pull_requests as (
    select * from {{ ref('stg_github__pull_requests') }}
)

select
    {{ dbt_utils.generate_surrogate_key(['p.repository', 'p.pr_number']) }} as pr_key,
    r.repository_key,
    co.contributor_key as author_key,
    {{ date_key('p.created_at') }} as opened_date_key,
    {{ date_key('p.merged_at') }} as merged_date_key,
    p.merged_at is not null as is_merged,
    case
        when p.merged_at is not null
            then datediff('hour', p.created_at, p.merged_at)
    end as time_to_merge_hours
from pull_requests p
{{ scd2_repository_join('p.repository', 'p.created_at::date') }}
left join {{ ref('dim_contributors') }} co
    on p.author_login = co.username

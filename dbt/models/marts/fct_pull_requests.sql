-- Pull request lifecycle fact: one row per PR. Repository resolved via the SCD2
-- half-open range on the PR open date; author via dim_contributors; opened/merged
-- date keys are inline YYYYMMDD references to dim_dates (merged is nullable).

with pull_requests as (
    select * from {{ ref('stg_github__pull_requests') }}
)

select
    {{ dbt_utils.generate_surrogate_key(['p.repository', 'p.pr_number']) }} as pr_key,
    r.repository_key,
    co.contributor_key as author_key,
    cast(strftime(p.created_at, '%Y%m%d') as integer) as opened_date_key,
    cast(strftime(p.merged_at, '%Y%m%d') as integer) as merged_date_key,
    p.merged_at is not null as is_merged,
    p.time_to_merge_hours,
    p.review_comments as review_count,
    p.comment_count,
    p.additions,
    p.deletions
from pull_requests p
left join {{ ref('dim_repositories') }} r
    on p.repository = r.repository_name
    and p.created_at::date >= r.valid_from
    and p.created_at::date < r.valid_to
left join {{ ref('dim_contributors') }} co
    on p.author_login = co.username

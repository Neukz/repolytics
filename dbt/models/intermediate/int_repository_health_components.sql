-- The five raw signals feeding the composite health score, one row per repository.
-- The trailing windows are relative to `current_date`, so this model is deliberately
-- non-deterministic: it describes health *as of the last run*, and the daily rebuild
-- is what keeps it current.

with repositories as (
    select repository_id, repository_name, stars
    from {{ ref('stg_github__repositories') }}
),

commits_90d as (
    select
        repository,
        count(*) as commits_90d
    from {{ ref('stg_github__commits') }}
    where committed_at >= current_date - interval '90 days'
    group by repository
),

prs_12m as (
    select
        repository,
        avg((merged_at is not null)::int) as pr_merge_rate
    from {{ ref('stg_github__pull_requests') }}
    where created_at >= current_date - interval '365 days'
    group by repository
),

issues_12m as (
    select
        repository,
        avg((state = 'closed')::int) as issue_close_rate
    from {{ ref('stg_github__issues') }}
    where created_at >= current_date - interval '365 days'
    group by repository
),

releases as (
    select
        repository,
        date_diff('day', max(published_at), current_date) as days_since_release
    from {{ ref('stg_github__releases') }}
    group by repository
)

select
    r.repository_id,
    r.repository_name,
    coalesce(c.commits_90d, 0) as commits_90d,
    coalesce(p.pr_merge_rate, 0) as pr_merge_rate,
    coalesce(i.issue_close_rate, 0) as issue_close_rate,
    -- Null means "never released", which decays the recency component to zero.
    rel.days_since_release,
    r.stars
from repositories r
left join commits_90d c on r.repository_name = c.repository
left join prs_12m p on r.repository_name = p.repository
left join issues_12m i on r.repository_name = i.repository
left join releases rel on r.repository_name = rel.repository

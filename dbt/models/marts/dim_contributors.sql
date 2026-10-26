-- Type 1 contributor dimension: one row per GitHub login, rebuilt each run. Derived
-- entirely from int_contributor_activity. Stats are commit/PR-based; issue-only
-- authors appear with zeroed counts.

with events as (
    select * from {{ ref('int_contributor_activity') }}
),

contributors as (
    select distinct username from events
),

commit_stats as (
    select
        username,
        min(event_date) as first_commit_date,
        max(event_date) as last_commit_date,
        count(*) as total_commits,
        count(distinct repository) as distinct_projects_count
    from events
    where activity_type = 'commit'
    group by username
),

pr_stats as (
    select
        username,
        count(*) filter (where activity_type = 'pr_opened') as total_prs_opened,
        count(*) filter (where activity_type = 'pr_merged') as total_prs_merged
    from events
    where activity_type in ('pr_opened', 'pr_merged')
    group by username
),

-- Most-committed-to project per contributor (ties broken alphabetically).
primary_project as (
    select username, repository as primary_project
    from (
        select
            username,
            repository,
            row_number() over (
                partition by username
                order by count(*) desc, repository
            ) as rn
        from events
        where activity_type = 'commit'
        group by username, repository
    )
    where rn = 1
)

select
    {{ dbt_utils.generate_surrogate_key(['c.username']) }} as contributor_key,
    c.username,
    cs.first_commit_date,
    cs.last_commit_date,
    coalesce(cs.total_commits, 0) as total_commits,
    coalesce(ps.total_prs_opened, 0) as total_prs_opened,
    coalesce(ps.total_prs_merged, 0) as total_prs_merged,
    coalesce(cs.distinct_projects_count, 0) as distinct_projects_count,
    pp.primary_project
from contributors c
left join commit_stats cs on c.username = cs.username
left join pr_stats ps on c.username = ps.username
left join primary_project pp on c.username = pp.username

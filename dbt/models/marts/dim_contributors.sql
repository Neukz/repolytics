-- Type 1 contributor dimension: one row per GitHub login, aggregated across the
-- commit, pull request, and issue staging models. Rebuilt in full each run.
-- Stats are commit/PR-based; issue-only authors appear with zeroed counts.

with commits as (
    select
        author_login as username,
        repository,
        committed_at
    from {{ ref('stg_github__commits') }}
    where author_login is not null
),

prs as (
    select
        author_login as username,
        merged_at
    from {{ ref('stg_github__pull_requests') }}
    where author_login is not null
),

contributors as (
    select username from commits
    union
    select username from prs
    union
    select author_login as username
    from {{ ref('stg_github__issues') }}
    where author_login is not null
),

commit_stats as (
    select
        username,
        min(committed_at::date) as first_commit_date,
        max(committed_at::date) as last_commit_date,
        count(*) as total_commits,
        count(distinct repository) as distinct_projects_count
    from commits
    group by username
),

pr_stats as (
    select
        username,
        count(*) as total_prs_opened,
        count(*) filter (where merged_at is not null) as total_prs_merged
    from prs
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
        from commits
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

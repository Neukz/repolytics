-- Aggregate fact: one row per contributor per month, pivoting int_contributor_activity
-- into commit / PR / issue counts. Foundation for retention analysis.

with monthly as (
    select
        username,
        event_month,
        count(*) filter (where activity_type = 'commit') as commits,
        count(*) filter (where activity_type = 'pr_opened') as prs_opened,
        count(*) filter (where activity_type = 'pr_merged') as prs_merged,
        count(*) filter (where activity_type = 'issue_opened') as issues_opened,
        count(*) filter (where activity_type = 'issue_closed') as issues_closed
    from {{ ref('int_contributor_activity') }}
    group by username, event_month
)

select
    {{ dbt_utils.generate_surrogate_key(['c.contributor_key', 'm.event_month']) }}
        as activity_key,
    c.contributor_key,
    m.username,
    m.event_month,
    {{ date_key('m.event_month') }} as month_date_key,
    m.commits,
    m.prs_opened,
    m.prs_merged,
    m.issues_opened,
    m.issues_closed
from monthly m
inner join {{ ref('dim_contributors') }} c on m.username = c.username

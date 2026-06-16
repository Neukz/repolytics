-- Tidy contributor activity event stream at username grain: one row per discrete
-- activity event. A reusable building block for monthly aggregation (and future PR /
-- health metrics). Each PR and issue contributes up to two events (opened, and
-- merged/closed) so each lands in the month it actually happened.

with commits as (
    select
        author_login as username,
        committed_at::date as event_date,
        'commit' as activity_type
    from {{ ref('stg_github__commits') }}
    where author_login is not null
),

prs_opened as (
    select
        author_login as username,
        created_at::date as event_date,
        'pr_opened' as activity_type
    from {{ ref('stg_github__pull_requests') }}
    where author_login is not null
),

prs_merged as (
    select
        author_login as username,
        merged_at::date as event_date,
        'pr_merged' as activity_type
    from {{ ref('stg_github__pull_requests') }}
    where author_login is not null and merged_at is not null
),

issues_opened as (
    select
        author_login as username,
        created_at::date as event_date,
        'issue_opened' as activity_type
    from {{ ref('stg_github__issues') }}
    where author_login is not null
),

issues_closed as (
    select
        author_login as username,
        closed_at::date as event_date,
        'issue_closed' as activity_type
    from {{ ref('stg_github__issues') }}
    where author_login is not null and closed_at is not null
),

events as (
    select * from commits
    union all
    select * from prs_opened
    union all
    select * from prs_merged
    union all
    select * from issues_opened
    union all
    select * from issues_closed
)

select
    username,
    event_date,
    date_trunc('month', event_date) as event_month,
    activity_type
from events

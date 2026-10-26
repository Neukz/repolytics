-- Composite project-health fact: one row per repository, scoring the five signals in
-- int_repository_health_components. Rebuilt each run, so it reads as health *as of*
-- the last run; `date_key` records which day that was.
--
-- Each component is scored absolutely against a fixed reference, so a project's score
-- is stable regardless of what else is in the warehouse. Rate signals (PR merge,
-- issue close) are used directly; unbounded signals (commits, stars) go through a
-- saturating log transform and release recency through exponential decay.

{%- set weight_activity = 0.30 %}
{%- set weight_pr_responsiveness = 0.20 %}
{%- set weight_issue_management = 0.20 %}
{%- set weight_release_recency = 0.15 %}
{%- set weight_popularity = 0.15 %}

{#- Value at which a component counts as fully healthy (half-life, for recency). -#}
{%- set target_commits_90d = 90 %}
{%- set ref_stars = 50000 %}
{%- set release_halflife_days = 180.0 %}

with components as (
    select * from {{ ref('int_repository_health_components') }}
),

scored as (
    select
        repository_id,
        repository_name,
        commits_90d,
        pr_merge_rate,
        issue_close_rate,
        days_since_release,
        stars,
        least(
            ln(1 + greatest(commits_90d, 0)) / ln(1 + {{ target_commits_90d }}), 1.0
        ) as c_activity,
        greatest(least(pr_merge_rate, 1.0), 0.0) as c_pr_responsiveness,
        greatest(least(issue_close_rate, 1.0), 0.0) as c_issue_management,
        -- Never released -> null days -> recency decays to zero.
        coalesce(
            pow(0.5, days_since_release / {{ release_halflife_days }}), 0.0
        ) as c_release_recency,
        least(ln(1 + greatest(stars, 0)) / ln(1 + {{ ref_stars }}), 1.0) as c_popularity
    from components
)

select
    {{ dbt_utils.generate_surrogate_key(['s.repository_id', 'current_date']) }}
        as health_key,
    s.repository_id,
    s.repository_name,
    r.repository_key,
    {{ date_key('current_date') }} as date_key,
    s.commits_90d,
    s.pr_merge_rate,
    s.issue_close_rate,
    s.days_since_release,
    s.stars,
    s.c_activity,
    s.c_pr_responsiveness,
    s.c_issue_management,
    s.c_release_recency,
    s.c_popularity,
    (
        s.c_activity * {{ weight_activity }}
        + s.c_pr_responsiveness * {{ weight_pr_responsiveness }}
        + s.c_issue_management * {{ weight_issue_management }}
        + s.c_release_recency * {{ weight_release_recency }}
        + s.c_popularity * {{ weight_popularity }}
    ) * 100.0 as health_score
from scored s
{{ scd2_repository_join('s.repository_name', 'current_date') }}

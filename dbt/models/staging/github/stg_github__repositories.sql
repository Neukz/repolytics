-- Structural cleaning over dlt's normalized `repositories` table. Topics are
-- re-aggregated from the dlt child table into a sorted comma string so the SCD2
-- snapshot's check_cols see a stable scalar.

with repositories as (
    select * from {{ source('github', 'repositories') }}
),

topics_src as (
    {{ source_or_empty('github', 'repositories__topics',
        {'value': 'varchar', '_dlt_parent_id': 'varchar'}) }}
),

topics as (
    select
        _dlt_parent_id,
        string_agg(value, ',' order by value) as topics
    from topics_src
    group by _dlt_parent_id
)

select
    r.id as repository_id,
    r.full_name as repository_name,
    r.name,
    r.owner__login as owner_login,
    r.description,
    r.stargazers_count as stars,
    r.forks_count as forks,
    r.open_issues_count as open_issues,
    r.language,
    r.license__spdx_id as license_spdx,
    t.topics,
    r.created_at,
    r.updated_at,
    r._loaded_at
from repositories r
left join topics t on r._dlt_id = t._dlt_parent_id

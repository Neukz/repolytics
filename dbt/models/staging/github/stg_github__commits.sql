-- Structural cleaning over dlt's normalized `commits` table. Merge commits (more
-- than one parent) are dropped using a count from the dlt `commits__parents` child table.

with commits as (
    select * from {{ source('github', 'commits') }}
),

parents_src as (
    {{ source_or_empty('github', 'commits__parents', {'_dlt_parent_id': 'varchar'}) }}
),

parent_counts as (
    select _dlt_parent_id, count(*) as parent_count
    from parents_src
    group by _dlt_parent_id
)

select
    c.sha as commit_sha,
    c._repo as repository,
    c.author__login as author_login,
    c.commit__author__name as author_name,
    c.commit__author__email as author_email,
    c.commit__author__date as committed_at,
    c.commit__message as message,
    c._loaded_at
from commits c
left join parent_counts p on c._dlt_id = p._dlt_parent_id
where coalesce(p.parent_count, 0) <= 1

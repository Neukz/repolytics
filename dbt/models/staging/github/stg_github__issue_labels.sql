-- Flattens dlt's `issues__labels` child table back to its parent issue, exposing a
-- repository + issue_number grain. Labels on PR-shaped issues are excluded to
-- match the issues staging filter.

with labels as (
    {{ source_or_empty('github', 'issues__labels',
        {'name': 'varchar', 'color': 'varchar', '_dlt_parent_id': 'varchar'}) }}
),

issues as (
    select * from {{ source('github', 'issues') }}
    where pull_request__url is null
)

select
    i._repo as repository,
    i.number as issue_number,
    l.name as label_name,
    l.color as label_color
from labels l
inner join issues i on l._dlt_parent_id = i._dlt_id

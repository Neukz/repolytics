-- Flattens dlt's `pull_requests__labels` child table back to its parent PR,
-- exposing a repository + pr_number grain.

with labels as (
    {{ source_or_empty('github', 'pull_requests__labels',
        {'name': 'varchar', 'color': 'varchar', '_dlt_parent_id': 'varchar'}) }}
),

pull_requests as (
    select * from {{ source('github', 'pull_requests') }}
)

select
    p._repo as repository,
    p.number as pr_number,
    l.name as label_name,
    l.color as label_color
from labels l
inner join pull_requests p on l._dlt_parent_id = p._dlt_id

-- Structural cleaning over dlt's `issues__labels` child table. One row per label
-- assignment.

with labels as (
    {{ source_or_empty('github', 'issues__labels',
        {'name': 'varchar', 'color': 'varchar', '_dlt_parent_id': 'varchar'}) }}
)

select
    _dlt_parent_id,
    name as label_name,
    color as label_color
from labels

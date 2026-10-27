-- Structural cleaning over dlt's `repositories__topics` child table. One row per
-- topic.

with topics as (
    {{ source_or_empty('github', 'repositories__topics',
        {'value': 'varchar', '_dlt_parent_id': 'varchar'}) }}
)

select
    _dlt_parent_id,
    value as topic
from topics

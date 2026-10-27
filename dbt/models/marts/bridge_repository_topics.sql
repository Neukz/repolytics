-- Bridge for the repository<->topic many-to-many; one row per (repository, topic).
-- GitHub only exposes current topics, so rows attach to the current dim_repositories
-- version rather than resolving a version per event date.

with topics as (
    select * from {{ ref('int_repository_topics') }}
)

select distinct
    r.repository_key,
    t.topic
from topics t
inner join {{ ref('dim_repositories') }} r
    on t.repository_id = r.repository_id
    and r.is_current

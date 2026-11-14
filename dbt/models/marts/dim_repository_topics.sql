-- Multi-valued repository attribute: one row per (current repository version, topic).
-- A topic has no attributes of its own, so this is a 1:N expansion of the dimension,
-- not a bridge to a second dimension. GitHub only exposes current topics, so rows
-- attach to the current dim_repositories version.

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

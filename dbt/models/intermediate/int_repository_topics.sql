-- Resolves dlt's `repositories__topics` child rows to their repository.
-- Grain: one row per (repository, topic).

select
    r.repository_id,
    r.repository_name,
    t.topic
from {{ ref('stg_github__repository_topics') }} t
inner join {{ ref('stg_github__repositories') }} r
    on t._dlt_parent_id = r._dlt_id

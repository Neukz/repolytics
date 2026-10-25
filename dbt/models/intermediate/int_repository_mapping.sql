-- Maps the mutable repository name (`owner/name`, as stamped by dlt in `_repo`)
-- to the immutable GitHub `repository_id`. Used by `scd2_repository_join` so that
-- facts resolve repository versions via the stable ID rather than the mutable
-- string, surviving renames and transfers.

-- Grain: one row per (current repository_name, repository_id). Re-adding a repo
-- under a new name will produce a second row for the same ID.

select distinct
    r.repository_name as repo,
    r.repository_id
from {{ ref('stg_github__repositories') }} r

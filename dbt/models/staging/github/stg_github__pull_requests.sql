-- Structural cleaning over dlt's normalized `pull_requests` table. Labels live in
-- the `pull_requests__labels` child table (see stg_github__pr_labels).

with pull_requests as (
    select * from {{ source('github', 'pull_requests') }}
)

select
    _repo as repository,
    number as pr_number,
    user__login as author_login,
    state,
    created_at,
    merged_at,
    -- dlt row id; the parent key the `pull_requests__labels` child rows point at.
    _dlt_id
from pull_requests

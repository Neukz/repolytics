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
    _loaded_at
from pull_requests

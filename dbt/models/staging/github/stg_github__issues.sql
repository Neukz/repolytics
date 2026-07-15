-- Structural cleaning over dlt's normalized `issues` table. The endpoint returns PRs
-- too; drop them (real issues have no `pull_request`). Labels: see stg_github__issue_labels.

with issues as (
    select * from {{ source('github', 'issues') }}
)

select
    _repo as repository,
    number as issue_number,
    user__login as author_login,
    state,
    created_at,
    closed_at,
    comments as comment_count,
    _loaded_at
from issues
where pull_request__url is null

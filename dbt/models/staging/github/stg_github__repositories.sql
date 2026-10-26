-- Structural cleaning over dlt's normalized `repositories` table. Topics live in the
-- `repositories__topics` child table (see stg_github__repository_topics); the
-- parent/child rejoin happens in int_repository_topics.

with repositories as (
    select * from {{ source('github', 'repositories') }}
)

select
    id as repository_id,
    full_name as repository_name,
    name,
    owner__login as owner_login,
    description,
    stargazers_count as stars,
    forks_count as forks,
    open_issues_count as open_issues,
    language,
    license__spdx_id as license_spdx,
    created_at,
    updated_at,
    -- dlt row id; the parent key the `repositories__topics` child rows point at.
    _dlt_id,
    _dlt_load_id
from repositories

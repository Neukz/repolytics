with source as (
    select data::json as d, _loaded_at
    from {{ source('github', 'repositories') }}
)

select
    (d ->> '$.id')::bigint as repository_id,
    d ->> '$.full_name' as repository_name,
    d ->> '$.name' as name,
    d ->> '$.owner.login' as owner_login,
    d ->> '$.description' as description,
    (d ->> '$.stargazers_count')::bigint as stars,
    (d ->> '$.forks_count')::bigint as forks,
    (d ->> '$.open_issues_count')::bigint as open_issues,
    d ->> '$.language' as language,
    d ->> '$.license.spdx_id' as license_spdx,
    d -> '$.topics' as topics,
    (d ->> '$.created_at')::timestamp as created_at,
    (d ->> '$.updated_at')::timestamp as updated_at,
    _loaded_at
from source

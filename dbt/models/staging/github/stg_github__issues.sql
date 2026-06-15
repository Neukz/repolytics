with source as (
    select data::json as d, _repo, _loaded_at
    from {{ source('github', 'issues') }}
)

select
    _repo as repository,
    (d ->> '$.number')::bigint as issue_number,
    d ->> '$.user.login' as author_login,
    d ->> '$.state' as state,
    (d ->> '$.state') = 'closed' as is_closed,
    (d ->> '$.created_at')::timestamp as created_at,
    (d ->> '$.closed_at')::timestamp as closed_at,
    case
        when (d ->> '$.closed_at') is not null then datediff(
            'hour',
            (d ->> '$.created_at')::timestamp,
            (d ->> '$.closed_at')::timestamp
        )
    end as time_to_close_hours,
    (d ->> '$.comments')::bigint as comment_count,
    d -> '$.labels' as labels,
    _loaded_at
from source
-- The issues endpoint returns PRs too; drop them (real issues have no `pull_request`).
where (d -> '$.pull_request') is null

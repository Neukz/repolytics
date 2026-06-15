with source as (
    select data::json as d, _repo, _loaded_at
    from {{ source('github', 'pull_requests') }}
)

select
    _repo as repository,
    (d ->> '$.number')::bigint as pr_number,
    d ->> '$.user.login' as author_login,
    d ->> '$.state' as state,
    (d ->> '$.created_at')::timestamp as created_at,
    (d ->> '$.merged_at')::timestamp as merged_at,
    (d ->> '$.additions')::bigint as additions,
    (d ->> '$.deletions')::bigint as deletions,
    (d ->> '$.review_comments')::bigint as review_comments,
    (d ->> '$.comments')::bigint as comment_count,
    case
        when (d ->> '$.merged_at') is not null then datediff(
            'hour',
            (d ->> '$.created_at')::timestamp,
            (d ->> '$.merged_at')::timestamp
        )
    end as time_to_merge_hours,
    d -> '$.labels' as labels,
    _loaded_at
from source

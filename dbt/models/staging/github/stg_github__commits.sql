with source as (
    select data::json as d, _repo, _loaded_at
    from {{ source('github', 'commits') }}
)

select
    d ->> '$.sha' as commit_sha,
    _repo as repository,
    d ->> '$.author.login' as author_login,
    d ->> '$.commit.author.name' as author_name,
    d ->> '$.commit.author.email' as author_email,
    (d ->> '$.commit.author.date')::timestamp as committed_at,
    (d ->> '$.stats.additions')::bigint as additions,
    (d ->> '$.stats.deletions')::bigint as deletions,
    d ->> '$.commit.message' as message,
    _loaded_at
from source
-- Drop merge commits (more than one parent); rows without `parents` are kept.
where coalesce(json_array_length(d -> '$.parents'), 0) <= 1

-- The `is_latest` flag is derived with a window function, so a mistake in its
-- partitioning would silently flag several capture days per repository and every
-- consumer reading `where is_latest` would double-count. Assert exactly one.

select
    repository_id,
    count(*) as flagged_rows
from {{ ref('fct_repository_metrics') }}
where is_latest
group by repository_id
having count(*) > 1

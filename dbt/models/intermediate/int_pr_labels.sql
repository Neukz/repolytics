-- Rejoins dlt's `pull_requests__labels` child rows to their parent pull request,
-- exposing a repository + pr_number grain.

select
    p.repository,
    p.pr_number,
    l.label_name,
    l.label_color
from {{ ref('stg_github__pr_labels') }} l
inner join {{ ref('stg_github__pull_requests') }} p
    on l._dlt_parent_id = p._dlt_id

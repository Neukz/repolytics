-- Rejoins dlt's `issues__labels` child rows to their parent issue, exposing a
-- repository + issue_number grain. Joining through stg_github__issues inherits that
-- model's PR filter, so the `pull_request__url is null` rule is stated exactly once.

select
    i.repository,
    i.issue_number,
    l.label_name,
    l.label_color
from {{ ref('stg_github__issue_labels') }} l
inner join {{ ref('stg_github__issues') }} i
    on l._dlt_parent_id = i._dlt_id

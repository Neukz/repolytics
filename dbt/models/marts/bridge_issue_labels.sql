-- Bridge for the issue<->label many-to-many; one row per (issue, label).
-- Recomputes the issue surrogate key the same way as fct_issues.

with issue_labels as (
    select * from {{ ref('stg_github__issue_labels') }}
)

select distinct
    {{ dbt_utils.generate_surrogate_key(['il.repository', 'il.issue_number']) }}
        as issue_key,
    dl.label_key
from issue_labels il
inner join {{ ref('dim_labels') }} dl on il.label_name = dl.label_name

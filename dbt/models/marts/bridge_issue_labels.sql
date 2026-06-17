-- Bridge table for the issue<->label many-to-many. Built from the flattened issue
-- label staging model; recomputes the issue surrogate key the same way as fct_issues
-- and resolves each label name to its label_key in dim_labels.
-- Grain: one row per (issue, label).

with issue_labels as (
    select * from {{ ref('stg_github__issue_labels') }}
)

select distinct
    {{ dbt_utils.generate_surrogate_key(['il.repository', 'il.issue_number']) }}
        as issue_key,
    dl.label_key
from issue_labels il
inner join {{ ref('dim_labels') }} dl on il.label_name = dl.label_name

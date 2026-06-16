-- Bridge table for the issue<->label many-to-many. Labels land in staging as a JSON
-- array per issue; we explode them, recompute the issue surrogate key the same way as
-- fct_issues, and resolve each label name to its label_key in dim_labels.
-- Grain: one row per (issue, label).

with issue_labels as (
    select
        repository,
        issue_number,
        unnest(json_extract(labels, '$[*]')) as label
    from {{ ref('stg_github__issues') }}
    where labels is not null
),

exploded as (
    select
        {{ dbt_utils.generate_surrogate_key(['repository', 'issue_number']) }} as issue_key,
        label ->> '$.name' as label_name
    from issue_labels
    where (label ->> '$.name') is not null
)

select distinct
    e.issue_key,
    dl.label_key
from exploded e
inner join {{ ref('dim_labels') }} dl on e.label_name = dl.label_name

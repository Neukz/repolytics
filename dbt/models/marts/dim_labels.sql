-- Type 1 label dimension: distinct issue/PR labels across all projects. Labels come
-- from the flattened dlt child-table staging models, deduped by name.

with labels as (
    select label_name, label_color from {{ ref('stg_github__issue_labels') }}
    union all
    select label_name, label_color from {{ ref('stg_github__pr_labels') }}
),

distinct_labels as (
    select
        label_name,
        max(label_color) as label_color
    from labels
    where label_name is not null
    group by label_name
)

select
    {{ dbt_utils.generate_surrogate_key(['label_name']) }} as label_key,
    label_name,
    label_color
from distinct_labels

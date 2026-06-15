-- Type 1 label dimension: distinct issue/PR labels across all projects. Labels land
-- in staging as a JSON array per row, so we explode the arrays and dedupe by name.

with labels_raw as (
    select labels
    from {{ ref('stg_github__pull_requests') }}
    where labels is not null
    union all
    select labels
    from {{ ref('stg_github__issues') }}
    where labels is not null
),

exploded as (
    select unnest(json_extract(labels, '$[*]')) as label
    from labels_raw
),

distinct_labels as (
    select
        label ->> '$.name' as label_name,
        max(label ->> '$.color') as label_color
    from exploded
    where (label ->> '$.name') is not null
    group by label ->> '$.name'
)

select
    {{ dbt_utils.generate_surrogate_key(['label_name']) }} as label_key,
    label_name,
    label_color
from distinct_labels

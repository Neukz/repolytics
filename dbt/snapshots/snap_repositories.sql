{% snapshot snap_repositories %}

{{
    config(
        unique_key='repository_id',
        strategy='check',
        check_cols=['description', 'language', 'license_spdx'],
    )
}}

-- SCD Type 2 history capture for repositories. Columns are listed explicitly rather
-- than `select *` so dlt's per-load `_dlt_id` never enters the version history.
select
    repository_id,
    repository_name,
    name,
    owner_login,
    description,
    stars,
    forks,
    open_issues,
    language,
    license_spdx,
    created_at,
    updated_at
from {{ ref('stg_github__repositories') }}

{% endsnapshot %}

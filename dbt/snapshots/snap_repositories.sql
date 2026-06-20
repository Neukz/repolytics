{% snapshot snap_repositories %}

{{
    config(
        unique_key='repository_id',
        strategy='check',
        check_cols=['description', 'language', 'license_spdx', 'topics'],
    )
}}

-- SCD Type 2 history capture for repositories.
select * from {{ ref('stg_github__repositories') }}

{% endsnapshot %}

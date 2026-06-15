{% snapshot snap_repositories %}

{{
    config(
        unique_key='repository_id',
        strategy='check',
        check_cols=['stars', 'forks', 'open_issues', 'description', 'topics'],
    )
}}

-- SCD Type 2 history capture for repositories.
select * from {{ ref('stg_github__repositories') }}

{% endsnapshot %}

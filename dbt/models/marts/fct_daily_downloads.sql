-- PyPI daily download fact: one row per package per day. `repository_key` resolves
-- through the `projects` seed (package -> repo) and the SCD2 join; nullable for
-- unmapped packages.

with downloads as (
    select * from {{ ref('stg_pypi__downloads') }}
)

select
    {{ dbt_utils.generate_surrogate_key(['d.package', 'd.download_date']) }}
        as download_key,
    d.package,
    r.repository_key,
    {{ date_key('d.download_date') }} as date_key,
    d.download_count
from downloads d
left join {{ ref('projects') }} p on d.package = p.package
{{ scd2_repository_join('p.repo', 'd.download_date') }}

-- SCD Type 2 repository dimension: a thin presentation model over snap_repositories.
-- The dbt snapshot owns the history (dbt_valid_from/to); here we reshape it into the
-- star-schema contract (surrogate key + valid_from/valid_to/is_current).

with versioned as (
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
        topics,
        created_at,
        updated_at,
        -- Full-resolution version timestamp drives the surrogate key so it stays
        -- unique even if a repo changes more than once on the same calendar day;
        -- valid_from/valid_to are kept at date grain for fact date-range joins.
        dbt_valid_from as version_ts,
        dbt_valid_from::date as valid_from,
        coalesce(dbt_valid_to::date, date '9999-12-31') as valid_to,
        dbt_valid_to is null as is_current
    from {{ ref('snap_repositories') }}
)

select
    {{ dbt_utils.generate_surrogate_key(['repository_id', 'version_ts']) }} as repository_key,
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
    topics,
    created_at,
    updated_at,
    valid_from,
    valid_to,
    is_current
from versioned

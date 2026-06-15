-- Fails if consecutive days in dim_dates are not exactly one day apart, i.e. the
-- generated date dimension has a gap. Passes when zero rows are returned.

with ordered as (
    select
        full_date,
        lead(full_date) over (order by full_date) as next_date
    from {{ ref('dim_dates') }}
)

select *
from ordered
where next_date is not null
  and next_date <> full_date + 1

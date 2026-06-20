with spine as (
    {{
        dbt_utils.date_spine(
            datepart="day",
            start_date="cast('2000-01-01' as date)",
            end_date="cast('2031-01-01' as date)"
        )
    }}
)

select
    cast(strftime(date_day, '%Y%m%d') as integer) as date_key,
    cast(date_day as date) as full_date,
    year(date_day) as year,
    quarter(date_day) as quarter,
    month(date_day) as month,
    monthname(date_day) as month_name,
    day(date_day) as day_of_month,
    dayofweek(date_day) as day_of_week,
    dayname(date_day) as day_name,
    dayofweek(date_day) in (0, 6) as is_weekend,
    week(date_day) as week_of_year
from spine

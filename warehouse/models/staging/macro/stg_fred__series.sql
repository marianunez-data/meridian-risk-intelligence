-- Silver: FRED observations, with a monthly key on every row.
select
    series_id,
    observation_date,
    date_trunc('month', observation_date)::date as observation_month,
    value
from {{ source('bronze', 'fred_series') }}
where value is not null

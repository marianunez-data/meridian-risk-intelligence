-- Gold: hourly transaction and fraud volumes for monitoring charts.
select
    hour_index,
    day_index,
    hour_of_day,
    count(*)                                        as transactions,
    sum(amount)                                     as total_amount,
    count(*) filter (where is_fraud)                as fraud_transactions,
    coalesce(sum(amount) filter (where is_fraud), 0) as fraud_amount
from {{ ref('stg_paysim__transactions') }}
group by all
order by hour_index

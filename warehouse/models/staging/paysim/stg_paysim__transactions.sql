{{ config(materialized='table') }}

-- Silver: mobile-money transactions. PaySim "step" = 1 simulated hour.
select
    row_number() over (order by step, nameOrig, nameDest, amount)  as transaction_id,
    step                                                           as hour_index,
    cast((step - 1) / 24 as integer) + 1                           as day_index,
    (step - 1) % 24                                                as hour_of_day,
    lower(type)                                                    as transaction_type,
    amount,
    nameOrig                                                       as origin_account,
    nameDest                                                       as destination_account,
    left(nameDest, 1) = 'M'                                        as is_merchant_destination,
    oldbalanceOrg                                                  as origin_balance_before,
    newbalanceOrig                                                 as origin_balance_after,
    oldbalanceDest                                                 as destination_balance_before,
    newbalanceDest                                                 as destination_balance_after,
    isFraud = 1                                                    as is_fraud,
    isFlaggedFraud = 1                                             as is_flagged_by_rules
from {{ source('bronze', 'paysim_transactions') }}

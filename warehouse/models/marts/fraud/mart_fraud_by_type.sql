-- Gold: fraud exposure by channel, and how much the incumbent rule engine catches.
select
    transaction_type,
    count(*)                                                       as transactions,
    sum(amount)                                                    as total_amount,
    count(*) filter (where is_fraud)                               as fraud_transactions,
    sum(amount) filter (where is_fraud)                            as fraud_amount,
    avg(case when is_fraud then 1.0 else 0 end)                    as fraud_rate,
    count(*) filter (where is_flagged_by_rules)                    as rule_alerts,
    count(*) filter (where is_flagged_by_rules and is_fraud)       as rule_true_positives,
    count(*) filter (where is_flagged_by_rules and is_fraud)
        / nullif(count(*) filter (where is_fraud), 0)              as rule_detection_rate
from {{ ref('stg_paysim__transactions') }}
group by transaction_type
order by fraud_amount desc nulls last

-- Q7. How much fraud does the incumbent rule engine miss?
select
    transaction_type,
    transactions,
    fraud_transactions,
    fraud_amount,
    fraud_rate,
    rule_alerts,
    rule_true_positives,
    rule_detection_rate,
    fraud_amount / sum(fraud_amount) over ()        as share_of_fraud_losses
from gold.mart_fraud_by_type
where fraud_transactions > 0
order by fraud_amount desc;

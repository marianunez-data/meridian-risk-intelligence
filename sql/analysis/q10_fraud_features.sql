-- Q10. Fraud features known at authorisation time, for transfers and cash-outs.
-- Post-transaction balances (newbalance*) are deliberately excluded: the
-- decision to block happens before the transaction posts.
-- Velocity features use RANGE windows over simulated hours on the destination
-- account, a common mule-account signal.
with tx as (
    select *
    from silver.stg_paysim__transactions
    where transaction_type in ('transfer', 'cash_out')
),
velocity as (
    select
        transaction_id,
        count(*) over w24 - 1                                        as dest_inbound_count_24h,
        coalesce(sum(amount) over w24, 0) - amount                   as dest_inbound_amount_24h,
        count(*) over w_all - 1                                      as dest_inbound_count_ever
    from tx
    window
        w24   as (partition by destination_account order by hour_index
                  range between 24 preceding and current row),
        w_all as (partition by destination_account order by hour_index, transaction_id
                  rows between unbounded preceding and current row)
)
select
    t.transaction_id,
    t.hour_index,
    t.day_index,
    t.hour_of_day,
    t.transaction_type,
    t.amount,
    ln(1 + t.amount)                                                      as log_amount,
    t.origin_balance_before,
    t.destination_balance_before,
    t.amount / nullif(t.origin_balance_before, 0)                         as amount_to_origin_balance,
    (t.origin_balance_before > 0 and abs(t.amount - t.origin_balance_before) <= 0.01)::int
                                                                          as drains_origin_account,
    (t.origin_balance_before = 0)::int                                    as origin_balance_zero,
    (t.destination_balance_before = 0)::int                               as destination_balance_zero,
    v.dest_inbound_count_24h,
    v.dest_inbound_amount_24h,
    v.dest_inbound_count_ever,
    (v.dest_inbound_count_ever = 0)::int                                  as destination_first_seen,
    t.is_flagged_by_rules::int                                            as rule_flag,
    t.is_fraud::int                                                       as is_fraud
from tx t
join velocity v using (transaction_id)
order by t.transaction_id;

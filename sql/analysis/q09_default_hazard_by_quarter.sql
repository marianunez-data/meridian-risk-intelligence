-- Q9. Quarterly default rate of the active book (a hazard rate).
-- Each loan is "active" from its issue quarter until it defaults, is paid off,
-- or reaches the snapshot. Uses an event-count pattern with running window
-- sums instead of exploding loans x quarters (2.26M x 48 rows).
with spans as (
    select
        cast(date_trunc('quarter', issue_month) as date)                       as start_q,
        cast(date_trunc('quarter', case
            when is_defaulted                then est_default_month
            when loan_status = 'Fully Paid'  then coalesce(last_payment_month, issue_month)
            else date '2019-03-01' end) as date)                                as end_q,
        is_defaulted
    from silver.int_loans__outcomes
    where not is_policy_exception
),
starts as (select start_q as q, count(*) as n_start from spans group by 1),
ends   as (select end_q as q, count(*) as n_end, count(*) filter (where is_defaulted) as n_default
           from spans group by 1),
grid as (
    select cast(t.q as date) as q,
           coalesce(s.n_start, 0) as n_start, coalesce(e.n_end, 0) as n_end, coalesce(e.n_default, 0) as n_default
    from range(date '2007-04-01', date '2019-01-01', interval 3 month) t(q)
    left join starts s on s.q = cast(t.q as date)
    left join ends   e on e.q = cast(t.q as date)
),
active as (
    select q, n_default,
           sum(n_start) over w - sum(n_end) over w + n_end as active_loans
    from grid
    window w as (order by q rows between unbounded preceding and current row)
)
select q as quarter, active_loans, n_default as defaults,
       n_default / nullif(active_loans, 0)                         as quarterly_default_rate,
       1 - power(1 - n_default / nullif(active_loans, 0), 4)       as annualised_default_rate
from active
where active_loans >= 5000
order by q;

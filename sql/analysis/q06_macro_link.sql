-- Q6. Does the economy at origination explain credit quality?
-- Joins quarterly portfolio outcomes to the macro mart.
select
    date_trunc('quarter', p.month)                                    as quarter,
    sum(p.loans_originated)                                           as loans,
    sum(p.bad_rate_24m * p.loans_originated) / sum(p.loans_originated) as bad_rate_24m,
    avg(p.share_subprime_efg)                                         as share_subprime_efg,
    avg(m.unemployment_rate)                                          as unemployment_rate,
    avg(m.baa_credit_spread)                                          as baa_credit_spread
from gold.mart_portfolio_monthly p
join gold.mart_macro_monthly m using (month)
where p.bad_rate_24m is not null
  and p.month >= date '2009-01-01'
group by 1
order by 1;

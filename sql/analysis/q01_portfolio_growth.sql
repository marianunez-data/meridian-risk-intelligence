-- Q1. How fast did the book grow, and how concentrated is growth in recent years?
-- Skills: aggregation, window functions (SUM OVER, LAG), derived ratios.
with yearly as (
    select
        year(issue_month)                 as issue_year,
        count(*)                          as loans,
        sum(funded_amount)                as funded_amount,
        avg(funded_amount)                as avg_ticket
    from gold.fct_loans
    group by 1
)
select
    issue_year,
    loans,
    funded_amount,
    avg_ticket,
    sum(funded_amount) over (order by issue_year)                      as cumulative_funded,
    funded_amount / lag(funded_amount) over (order by issue_year) - 1   as yoy_growth,
    funded_amount / sum(funded_amount) over ()                          as share_of_book
from yearly
order by issue_year;

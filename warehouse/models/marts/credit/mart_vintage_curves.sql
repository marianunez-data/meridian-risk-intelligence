-- Gold: cumulative default rate by origination quarter and months on book.
-- The classic credit-risk view: does each new cohort default faster or slower
-- than the ones before it?
{%- set snapshot = "date '" ~ var('snapshot_date') ~ "'" %}

with base as (
    select
        cast(date_trunc('quarter', issue_month) as date) as vintage_quarter,
        term_months,
        funded_amount,
        is_defaulted,
        months_to_default
    from {{ ref('int_loans__outcomes') }}
),

vintages as (
    select vintage_quarter, term_months, count(*) as loans, sum(funded_amount) as funded_amount
    from base
    group by all
),

defaults as (
    select vintage_quarter, term_months, months_to_default as months_on_book,
           count(*) as defaults, sum(funded_amount) as defaulted_amount
    from base
    where is_defaulted
    group by all
),

grid as (
    -- Only show months that every loan in the vintage has had time to reach.
    select v.*, m.months_on_book
    from vintages v
    cross join range(0, 61) as m(months_on_book)
    where m.months_on_book <= v.term_months
      and m.months_on_book <= datediff('month', v.vintage_quarter + interval 2 month, {{ snapshot }})
)

select
    g.vintage_quarter,
    year(g.vintage_quarter)                                                    as vintage_year,
    g.term_months,
    g.months_on_book,
    g.loans,
    g.funded_amount,
    sum(coalesce(d.defaults, 0)) over w                                        as cumulative_defaults,
    sum(coalesce(d.defaults, 0)) over w / g.loans                              as cumulative_default_rate,
    sum(coalesce(d.defaulted_amount, 0)) over w / g.funded_amount              as cumulative_default_rate_amount
from grid g
left join defaults d using (vintage_quarter, term_months, months_on_book)
window w as (partition by g.vintage_quarter, g.term_months order by g.months_on_book)

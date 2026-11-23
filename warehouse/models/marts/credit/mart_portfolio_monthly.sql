-- Gold: portfolio KPIs by origination month, joined to the macro backdrop.
with loans as (
    select * from {{ ref('fct_loans') }}
),

kpis as (
    select
        issue_month                                                           as month,
        count(*)                                                              as loans_originated,
        sum(funded_amount)                                                    as funded_amount,
        sum(funded_amount * interest_rate) / sum(funded_amount)               as weighted_interest_rate,
        avg(fico_score)                                                       as avg_fico_score,
        avg(debt_to_income)                                                   as avg_debt_to_income,
        avg(case when grade in ('A', 'B') then 1.0 else 0 end)                as share_prime_ab,
        avg(case when grade in ('E', 'F', 'G') then 1.0 else 0 end)           as share_subprime_efg,
        avg(case when term_months = 60 then 1.0 else 0 end)                   as share_60_month,
        avg(case when is_bad_24m then 1.0 else 0 end)
            filter (where has_full_window)                                    as bad_rate_24m,
        avg(case when is_defaulted then 1.0 else 0 end)                       as default_rate_to_date,
        sum(exposure_at_default)                                              as defaulted_exposure,
        sum(exposure_at_default - net_recoveries)                             as realised_credit_loss,
        sum(interest_received)                                                as interest_income
    from loans
    group by issue_month
)

select
    k.*,
    m.unemployment_rate,
    m.fed_funds_rate,
    m.baa_credit_spread,
    m.real_gdp_growth_yoy
from kpis k
left join {{ ref('mart_macro_monthly') }} m using (month)
order by month

-- Data audit: validity and consistency rules evaluated in one pass.
-- Each rule returns the number of failing loans; the notebook turns this into
-- a scorecard with severity and the action taken in cleaning.
with s as (select * from silver.stg_lending_club__loans),
amort as (
    -- Recompute the monthly instalment from amount, rate and term with the
    -- annuity formula and compare it with the instalment Lending Club recorded.
    select abs(funded_amount * (interest_rate / 12) / (1 - power(1 + interest_rate / 12, -term_months))
               - installment_amount) / installment_amount as rel_diff
    from s
)
select 'validity'    as dimension, 'Debt-to-income is negative'                          as rule, count(*) filter (where debt_to_income < 0)                      as failing_rows from s
union all select 'validity',    'Debt-to-income above 100% of income',                       count(*) filter (where debt_to_income > 1)                       from s
union all select 'validity',    'Annual income is zero or negative',                         count(*) filter (where annual_income <= 0)                       from s
union all select 'validity',    'Annual income above USD 1M',                                count(*) filter (where annual_income > 1e6)                      from s
union all select 'validity',    'Revolving utilisation above 150%',                          count(*) filter (where revolving_utilization > 1.5)              from s
union all select 'validity',    'Home ownership coded ANY / NONE / OTHER',                   count(*) filter (where home_ownership in ('ANY', 'NONE', 'OTHER')) from s
union all select 'consistency', 'Funded amount above requested amount',                      count(*) filter (where funded_amount > loan_amount)              from s
union all select 'consistency', 'FICO low bound above high bound',                           count(*) filter (where fico_range_low > fico_range_high)         from s
union all select 'consistency', 'First credit line opened after the loan',                   count(*) filter (where earliest_credit_line_month > issue_month) from s
union all select 'consistency', 'Instalment differs from annuity formula by more than 1%',   count(*) filter (where rel_diff > 0.01)                          from amort
union all select 'uniqueness',  'Duplicate loan_id',                                         count(*) - count(distinct loan_id)                               from s
union all select 'uniqueness',  'Possible duplicate application (same month, amount, income, zip, title, DTI, FICO)',
          count(*) - (select count(*) from (select distinct issue_month, loan_amount, annual_income, zip3,
                                                            employment_title, debt_to_income, fico_score from s))
          from s;

-- Silver: one row per company with its latest FY annual figures, pivoted wide.
-- Balance sheet tags are taken at the period end (duration 0); income and
-- cash-flow tags over the full year (duration 4).

with filings as (

    select *
    from {{ ref('stg_sec__submissions') }}
    qualify row_number() over (partition by company_cik order by period_end_date desc, filed_date desc) = 1

),

vals as (

    select v.*, f.company_cik
    from {{ ref('stg_sec__financial_values') }} v
    join filings f
      on v.filing_id = f.filing_id
     and v.value_date = f.period_end_date

),

pivoted as (

    select
        company_cik,
        max(value_usd) filter (where tag = 'Assets' and duration_quarters = 0)                              as total_assets,
        max(value_usd) filter (where tag = 'AssetsCurrent' and duration_quarters = 0)                       as current_assets,
        max(value_usd) filter (where tag = 'Liabilities' and duration_quarters = 0)                         as total_liabilities_reported,
        max(value_usd) filter (where tag = 'LiabilitiesCurrent' and duration_quarters = 0)                  as current_liabilities,
        max(value_usd) filter (where tag = 'LiabilitiesAndStockholdersEquity' and duration_quarters = 0)    as liabilities_and_equity,
        max(value_usd) filter (where tag = 'StockholdersEquity' and duration_quarters = 0)                  as book_equity,
        max(value_usd) filter (where tag = 'RetainedEarningsAccumulatedDeficit' and duration_quarters = 0)  as retained_earnings,
        max(value_usd) filter (where tag = 'CashAndCashEquivalentsAtCarryingValue' and duration_quarters = 0) as cash,
        max(value_usd) filter (where tag = 'LongTermDebtNoncurrent' and duration_quarters = 0)              as long_term_debt,
        max(value_usd) filter (where tag = 'OperatingIncomeLoss' and duration_quarters = 4)                 as operating_income,
        coalesce(
            max(value_usd) filter (where tag = 'IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest' and duration_quarters = 4),
            max(value_usd) filter (where tag = 'IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments' and duration_quarters = 4)
        )                                                                                                   as pretax_income,
        max(value_usd) filter (where tag = 'NetIncomeLoss' and duration_quarters = 4)                       as net_income,
        max(value_usd) filter (where tag = 'InterestExpense' and duration_quarters = 4)                     as interest_expense,
        max(value_usd) filter (where tag = 'NetCashProvidedByUsedInOperatingActivities' and duration_quarters = 4) as operating_cash_flow,
        coalesce(
            max(value_usd) filter (where tag = 'Revenues' and duration_quarters = 4),
            max(value_usd) filter (where tag = 'RevenueFromContractWithCustomerExcludingAssessedTax' and duration_quarters = 4),
            max(value_usd) filter (where tag = 'SalesRevenueNet' and duration_quarters = 4)
        )                                                                                                   as revenue
    from vals
    group by company_cik

)

select
    f.company_cik,
    f.company_name,
    f.sic_code,
    f.state_code,
    f.fiscal_year,
    f.period_end_date,
    p.* exclude (company_cik),
    -- Many filers omit the Liabilities tag; derive it from the balance sheet identity.
    coalesce(p.total_liabilities_reported, p.liabilities_and_equity - p.book_equity) as total_liabilities,
    -- EBIT: operating income when reported, otherwise pre-tax income plus interest.
    coalesce(p.operating_income, p.pretax_income + coalesce(p.interest_expense, 0))  as ebit,
    case when p.operating_income is not null then 'operating_income'
         when p.pretax_income is not null    then 'pretax_plus_interest' end         as ebit_source
from filings f
join pivoted p using (company_cik)

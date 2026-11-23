{{ config(materialized='table') }}

-- Silver: only the XBRL tags needed for supplier financial health, consolidated
-- (no segment, no co-registrant), in USD.
with tags as (
    select * from (values
        ('Assets'), ('AssetsCurrent'), ('Liabilities'), ('LiabilitiesCurrent'),
        ('LiabilitiesAndStockholdersEquity'), ('StockholdersEquity'),
        ('RetainedEarningsAccumulatedDeficit'), ('OperatingIncomeLoss'), ('NetIncomeLoss'),
        ('Revenues'), ('RevenueFromContractWithCustomerExcludingAssessedTax'), ('SalesRevenueNet'),
        ('NetCashProvidedByUsedInOperatingActivities'), ('CashAndCashEquivalentsAtCarryingValue'),
        ('LongTermDebtNoncurrent'), ('InterestExpense'),
        ('IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest'),
        ('IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments')
    ) as t(tag)
)

select
    n.adsh                                      as filing_id,
    n.tag,
    cast(strptime(n.ddate, '%Y%m%d') as date)   as value_date,
    cast(n.qtrs as integer)                     as duration_quarters,  -- 0 = balance sheet, 4 = full year
    try_cast(n.value as double)                 as value_usd
from {{ source('bronze', 'sec_num') }} n
join tags using (tag)
where n.uom = 'USD'
  and coalesce(n.segments, '') = ''
  and coalesce(n.coreg, '') = ''
  and n.qtrs in ('0', '4')
  and try_cast(n.value as double) is not null

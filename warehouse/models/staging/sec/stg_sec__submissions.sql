-- Silver: one row per annual report (10-K) filed by a US operating company.
select
    adsh                                   as filing_id,
    cast(cik as integer)                   as company_cik,
    name                                   as company_name,
    try_cast(sic as integer)               as sic_code,
    countryba                              as country_code,
    stprba                                 as state_code,
    form,
    cast(strptime(period, '%Y%m%d') as date) as period_end_date,
    try_cast(fy as integer)                as fiscal_year,
    cast(strptime(filed, '%Y%m%d') as date)  as filed_date,
    source_quarter
from {{ source('bronze', 'sec_sub') }}
where form = '10-K'
  and countryba = 'US'
  and sic is not null

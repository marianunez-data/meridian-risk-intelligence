-- Gold: financial health score for every US public company that filed a
-- FY2018 10-K. Uses Altman Z'' (1995), the variant built for non-manufacturers
-- and firms without a market price, which is how procurement sees most suppliers.
--   Z'' = 6.56 X1 + 3.26 X2 + 6.72 X3 + 1.05 X4
--   X1 = working capital / total assets       (liquidity)
--   X2 = retained earnings / total assets     (cumulative profitability)
--   X3 = EBIT / total assets                  (operating efficiency)
--   X4 = book equity / total liabilities      (leverage)
-- Zones: > 2.60 safe, 1.10 to 2.60 grey, < 1.10 distress.

with fin as (
    select * from {{ ref('int_sec__supplier_financials') }}
    where total_assets > 0
),

ratios as (
    select
        *,
        (current_assets - current_liabilities) / total_assets         as x1_working_capital_to_assets,
        retained_earnings / total_assets                              as x2_retained_earnings_to_assets,
        ebit / total_assets                                           as x3_ebit_to_assets,
        book_equity / nullif(total_liabilities, 0)                    as x4_equity_to_liabilities,
        current_assets / nullif(current_liabilities, 0)               as current_ratio,
        total_liabilities / nullif(book_equity, 0)                    as debt_to_equity,
        ebit / nullif(interest_expense, 0)                            as interest_coverage,
        net_income / nullif(revenue, 0)                               as net_margin,
        operating_cash_flow / nullif(total_liabilities, 0)            as cash_flow_to_liabilities
    from fin
),

scored as (
    select
        *,
        6.56 * x1_working_capital_to_assets
      + 3.26 * x2_retained_earnings_to_assets
      + 6.72 * x3_ebit_to_assets
      + 1.05 * least(x4_equity_to_liabilities, 10)                    as altman_z_double_prime,
        (x1_working_capital_to_assets is not null
         and x2_retained_earnings_to_assets is not null
         and x3_ebit_to_assets is not null
         and x4_equity_to_liabilities is not null)                    as is_fully_scored
    from ratios
)

select
    s.*,
    sd.sector_name,
    sd.is_procurement_relevant,
    case
        when not s.is_fully_scored                 then 'Unscored'
        when s.altman_z_double_prime > 2.60        then 'Safe'
        when s.altman_z_double_prime >= 1.10       then 'Grey'
        else 'Distress'
    end                                                               as altman_zone
from scored s
left join {{ ref('sic_divisions') }} sd
  on s.sic_code between sd.sic_from and sd.sic_to

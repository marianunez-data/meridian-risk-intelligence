-- Gold: one row per month with every macro driver, quarterly series
-- carried forward so they can be joined to monthly loan data.
with monthly as (
    select
        observation_month                                               as month,
        avg(value) filter (where series_id = 'UNRATE')                  as unemployment_rate,
        avg(value) filter (where series_id = 'FEDFUNDS')                as fed_funds_rate,
        avg(value) filter (where series_id = 'CPIAUCSL')                as cpi_index,
        avg(value) filter (where series_id = 'BAA10Y')                  as baa_credit_spread,
        avg(value) filter (where series_id = 'GDPC1')                   as real_gdp,
        avg(value) filter (where series_id = 'DRCCLACBS')               as card_delinquency_rate,
        avg(value) filter (where series_id = 'CORCCACBS')               as card_chargeoff_rate
    from {{ ref('stg_fred__series') }}
    where observation_month >= date '1985-01-01'
    group by observation_month
),

filled as (
    select
        month,
        unemployment_rate,
        fed_funds_rate,
        cpi_index,
        baa_credit_spread,
        last_value(real_gdp ignore nulls)              over w as real_gdp,
        last_value(card_delinquency_rate ignore nulls) over w as card_delinquency_rate,
        last_value(card_chargeoff_rate ignore nulls)   over w as card_chargeoff_rate
    from monthly
    window w as (order by month rows between unbounded preceding and current row)
)

select
    month,
    unemployment_rate,
    fed_funds_rate,
    baa_credit_spread,
    card_delinquency_rate,
    card_chargeoff_rate,
    real_gdp,
    cpi_index / lag(cpi_index, 12) over (order by month) - 1   as cpi_inflation_yoy,
    real_gdp  / lag(real_gdp, 12)  over (order by month) - 1   as real_gdp_growth_yoy,
    unemployment_rate - lag(unemployment_rate, 12) over (order by month) as unemployment_change_yoy
from filled
order by month

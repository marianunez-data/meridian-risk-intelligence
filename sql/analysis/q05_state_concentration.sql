-- Q5. Geographic concentration: top 3 states per census region, plus the
-- Herfindahl-Hirschman Index (HHI) for the whole book.
-- Skills: joins to a dimension, DENSE_RANK, QUALIFY, scalar subquery.
with by_state as (
    select
        d.census_region,
        d.state_name,
        sum(f.funded_amount)                                       as exposure,
        avg(f.is_bad_24m::int) filter (where f.has_full_window)    as bad_rate_24m
    from gold.fct_loans f
    join gold.dim_geography d using (state_code)
    group by all
),
shares as (
    select *, exposure / sum(exposure) over () as share_of_book
    from by_state
)
select
    census_region,
    state_name,
    exposure,
    share_of_book,
    bad_rate_24m,
    dense_rank() over (partition by census_region order by exposure desc)   as rank_in_region,
    (select sum(power(share_of_book * 100, 2)) from shares)                 as portfolio_hhi
from shares
qualify rank_in_region <= 3
order by census_region, rank_in_region;

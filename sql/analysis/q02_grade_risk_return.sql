-- Q2. Is Meridian paid enough for the risk it takes in each grade?
-- Compares the interest rate charged with the observed 24-month bad rate and
-- realised loss. Skills: conditional aggregation, FILTER, window share.
select
    g.grade,
    count(*)                                                            as loans,
    count(*) / sum(count(*)) over ()                                    as share_of_loans,
    avg(f.interest_rate)                                                as avg_interest_rate,
    avg(f.is_bad_24m::int) filter (where f.has_full_window)             as bad_rate_24m,
    avg(f.is_defaulted::int) filter (where f.is_resolved)               as lifetime_default_rate_resolved,
    sum(f.exposure_at_default - f.net_recoveries) filter (where f.is_resolved)
        / sum(f.funded_amount) filter (where f.is_resolved)             as realised_loss_rate_resolved,
    avg(f.loss_given_default)                                           as avg_lgd
from gold.fct_loans f
join gold.dim_risk_grade g using (sub_grade)
group by g.grade
order by g.grade;

-- Q3. Why the naive default rate is misleading for recent vintages.
-- A loan issued in 2018 has had at most 15 months to default. Comparing the
-- naive "defaulted so far" rate with the windowed 24-month rate shows the bias
-- and justifies the target definition and the out-of-time split.
select
    year(issue_month)                                                 as issue_year,
    count(*)                                                          as loans,
    min(months_observed)                                              as min_months_observed,
    avg(is_defaulted::int)                                            as naive_default_rate_to_date,
    avg(is_bad_24m::int) filter (where has_full_window)               as bad_rate_24m,
    avg(has_full_window::int)                                         as share_with_full_window,
    any_value(dataset_split)                                          as dataset_split
from gold.fct_loans
group by 1
order by 1;

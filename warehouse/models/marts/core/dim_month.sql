-- Gold: monthly calendar covering the full portfolio history.
select
    cast(m as date)                                   as month,
    year(m)                                           as year,
    quarter(m)                                        as quarter,
    month(m)                                          as month_of_year,
    strftime(m, '%Y-Q') || quarter(m)                 as year_quarter,
    strftime(m, '%b %Y')                              as month_label
from range(date '2007-01-01', date '2020-01-01', interval 1 month) t(m)

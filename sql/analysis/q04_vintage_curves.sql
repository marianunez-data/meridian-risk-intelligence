-- Q4. Vintage curves: cumulative default rate by months on book, 36-month loans.
select vintage_year, months_on_book,
       sum(cumulative_defaults) / sum(loans) as cumulative_default_rate
from gold.mart_vintage_curves
where term_months = 36
  and vintage_year between 2012 and 2018
group by all
order by vintage_year, months_on_book;

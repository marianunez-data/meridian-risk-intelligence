-- Q8. Supplier financial health by sector (procurement-relevant sectors,
-- companies with at least USD 50M revenue, i.e. realistic suppliers).
select
    sector_name,
    count(*)                                                          as companies,
    avg((altman_zone = 'Safe')::int)                                  as share_safe,
    avg((altman_zone = 'Grey')::int)                                  as share_grey,
    avg((altman_zone = 'Distress')::int)                              as share_distress,
    median(altman_z_double_prime)                                     as median_z_score
from gold.mart_supplier_health
where is_procurement_relevant
  and altman_zone <> 'Unscored'
  and revenue >= 50e6
group by 1
order by companies desc;

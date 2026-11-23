-- Gold: Lending Club sub-grades ordered from safest (A1 = 1) to riskiest (G5 = 35).
select distinct
    sub_grade,
    grade,
    (ascii(grade) - ascii('A')) * 5 + cast(right(sub_grade, 1) as integer) as risk_rank
from {{ ref('stg_lending_club__loans') }}
order by risk_rank

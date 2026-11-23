-- Every loan in bronze (minus the 33 footer rows) must survive to the fact table.
with b as (select count(*) n from {{ source('bronze', 'lending_club_loans') }} where try_cast(id as bigint) is not null),
     f as (select count(*) n from {{ ref('fct_loans') }})
select b.n as bronze_loans, f.n as fact_loans from b, f where b.n <> f.n

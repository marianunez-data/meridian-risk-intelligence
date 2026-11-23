-- Gold: US states with census region, from a version-controlled seed.
select * from {{ ref('us_states') }}

-- A loan may carry a 24-month label only if 24 months have been observed.
select loan_id
from {{ ref('int_loans__outcomes') }}
where (is_bad_24m is not null) <> has_full_window

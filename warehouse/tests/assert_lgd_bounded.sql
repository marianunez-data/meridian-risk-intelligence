-- LGD is a share of exposure, so it must sit in [0, 1].
select loan_id, loss_given_default
from {{ ref('mart_lgd_base') }}
where loss_given_default < 0 or loss_given_default > 1

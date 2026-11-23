-- Gold: defaulted loans whose recoveries have had time to season.
-- Used to fit the Loss Given Default and Exposure at Default models.
select
    f.loan_id,
    f.issue_month,
    f.est_default_month,
    f.dataset_split,
    f.grade,
    f.term_months,
    f.loan_purpose,
    f.home_ownership,
    f.funded_amount,
    f.interest_rate,
    f.annual_income,
    f.fico_score,
    f.debt_to_income,
    f.months_to_default,
    f.exposure_at_default,
    f.exposure_at_default / nullif(f.funded_amount, 0)  as ead_ratio,
    f.net_recoveries,
    f.loss_given_default
from {{ ref('fct_loans') }} f
where f.is_defaulted
  and f.has_seasoned_recovery
  and f.exposure_at_default > 0

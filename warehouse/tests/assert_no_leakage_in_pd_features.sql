-- Fails if any post-origination column ever reaches the PD modelling table.
select column_name
from information_schema.columns
where table_schema = 'gold'
  and table_name = 'mart_pd_features'
  and column_name in (
      'loan_status', 'total_payments', 'principal_repaid', 'interest_received',
      'gross_recoveries', 'recovery_fees', 'outstanding_principal', 'last_payment_month',
      'had_hardship_plan', 'had_debt_settlement', 'exposure_at_default',
      'loss_given_default', 'est_default_month', 'months_to_default'
  )

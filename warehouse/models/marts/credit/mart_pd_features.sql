-- Gold: modelling table for the Probability of Default (PD) model.
-- Contract: only information available on the application date, plus the
-- target and the split label. Post-origination columns are excluded by
-- construction; tests/assert_no_leakage_in_pd_features.sql enforces it.
select
    loan_id,
    issue_month,
    dataset_split,
    is_bad_24m                                                        as target_bad_24m,

    -- Lending Club's own risk view, kept only as a benchmark to beat.
    grade                                                             as benchmark_grade,
    sub_grade                                                         as benchmark_sub_grade,
    interest_rate                                                     as benchmark_interest_rate,

    -- product
    term_months,
    loan_amount,
    installment_amount,
    loan_purpose,
    application_type,

    -- borrower. Joint applications store household income and DTI in
    -- separate columns and leave the individual ones empty or zero (found in
    -- the data audit, notebook 02), so the household figures are used.
    application_type = 'joint app'                                    as is_joint_application,
    employment_years,
    home_ownership,
    {{ effective('annual_income') }}                                  as annual_income,
    income_verification,
    state_code,
    {{ effective('debt_to_income') }}                                 as debt_to_income,

    -- bureau
    fico_score,
    delinquencies_2y,
    inquiries_6m,
    months_since_last_delinquency,
    months_since_last_public_record,
    open_accounts,
    total_accounts,
    public_records,
    public_bankruptcies,
    tax_liens,
    revolving_balance,
    revolving_utilization,
    mortgage_accounts,
    total_current_balance,
    total_credit_limit,
    total_revolving_limit,
    bankcard_utilization,
    bankcard_open_to_buy,
    avg_current_balance,
    accounts_opened_24m,
    accounts_opened_12m,
    active_revolving_accounts,
    pct_bankcards_over_75_util,
    pct_accounts_never_delinquent,
    months_since_oldest_revolving,
    months_since_recent_account,
    months_since_recent_inquiry,
    accounts_ever_120dpd,
    collections_12m,

    -- engineered ratios (all computable at application)
    datediff('month', earliest_credit_line_month, issue_month)        as credit_history_months,
    loan_amount / nullif({{ effective('annual_income') }}, 0)          as loan_to_income,
    installment_amount * 12 / nullif({{ effective('annual_income') }}, 0) as payment_to_income,
    revolving_balance / nullif({{ effective('annual_income') }}, 0)    as revolving_balance_to_income,

    -- Bureau attributes (bankcard, mortgage, balances, recent inquiries) only
    -- exist from 2012 onwards. Models train on this era (notebook 03).
    issue_month >= date '2012-01-01'                                  as is_full_bureau_era
from {{ ref('int_loans__outcomes') }}
where not is_policy_exception

{{ config(materialized='table') }}

-- Silver: one clean, typed, renamed row per funded loan.
-- Rules applied here are technical only (types, names, units). Business
-- definitions such as "default" live in the intermediate layer.

with source as (

    select * from {{ source('bronze', 'lending_club_loans') }}

),

cleaned as (

    select
        -- keys and dates
        try_cast(id as bigint)                                   as loan_id,
        {{ parse_month('issue_d') }}                             as issue_month,
        {{ parse_month('earliest_cr_line') }}                    as earliest_credit_line_month,
        {{ parse_month('last_pymnt_d') }}                        as last_payment_month,

        -- product
        cast(regexp_extract(term, '(\d+)', 1) as integer)        as term_months,
        loan_amnt                                                as loan_amount,
        funded_amnt                                              as funded_amount,
        int_rate / 100.0                                         as interest_rate,
        installment                                              as installment_amount,
        grade,
        sub_grade,
        lower(purpose)                                           as loan_purpose,
        lower(application_type)                                  as application_type,
        initial_list_status,

        -- borrower (known at application)
        nullif(trim(emp_title), '')                              as employment_title,
        case
            when emp_length = '< 1 year'  then 0
            when emp_length = '10+ years' then 10
            else try_cast(regexp_extract(emp_length, '(\d+)', 1) as integer)
        end                                                      as employment_years,
        upper(home_ownership)                                    as home_ownership,
        annual_inc                                               as annual_income,
        verification_status                                      as income_verification,
        addr_state                                               as state_code,
        zip_code                                                 as zip3,
        dti / 100.0                                              as debt_to_income,
        dti_joint / 100.0                                        as debt_to_income_joint,
        annual_inc_joint                                         as annual_income_joint,

        -- credit bureau (known at application)
        fico_range_low,
        fico_range_high,
        (fico_range_low + fico_range_high) / 2.0                 as fico_score,
        delinq_2yrs                                              as delinquencies_2y,
        inq_last_6mths                                           as inquiries_6m,
        mths_since_last_delinq                                   as months_since_last_delinquency,
        mths_since_last_record                                   as months_since_last_public_record,
        open_acc                                                 as open_accounts,
        total_acc                                                as total_accounts,
        pub_rec                                                  as public_records,
        pub_rec_bankruptcies                                     as public_bankruptcies,
        tax_liens,
        revol_bal                                                as revolving_balance,
        revol_util / 100.0                                       as revolving_utilization,
        mort_acc                                                 as mortgage_accounts,
        tot_cur_bal                                              as total_current_balance,
        tot_hi_cred_lim                                          as total_credit_limit,
        total_rev_hi_lim                                         as total_revolving_limit,
        total_bc_limit                                           as total_bankcard_limit,
        bc_util / 100.0                                          as bankcard_utilization,
        bc_open_to_buy                                           as bankcard_open_to_buy,
        avg_cur_bal                                              as avg_current_balance,
        acc_open_past_24mths                                     as accounts_opened_24m,
        num_tl_op_past_12m                                       as accounts_opened_12m,
        num_actv_rev_tl                                          as active_revolving_accounts,
        percent_bc_gt_75 / 100.0                                 as pct_bankcards_over_75_util,
        pct_tl_nvr_dlq / 100.0                                   as pct_accounts_never_delinquent,
        mo_sin_old_rev_tl_op                                     as months_since_oldest_revolving,
        mo_sin_rcnt_tl                                           as months_since_recent_account,
        mths_since_recent_inq                                    as months_since_recent_inquiry,
        num_accts_ever_120_pd                                    as accounts_ever_120dpd,
        collections_12_mths_ex_med                               as collections_12m,
        acc_now_delinq                                           as accounts_now_delinquent,

        -- performance (post-origination: never a model feature)
        loan_status                                              as loan_status_raw,
        regexp_replace(loan_status,
            '^Does not meet the credit policy\. Status:', '')    as loan_status,
        loan_status like 'Does not meet the credit policy%'      as is_policy_exception,
        total_pymnt                                              as total_payments,
        total_rec_prncp                                          as principal_repaid,
        total_rec_int                                            as interest_received,
        total_rec_late_fee                                       as late_fees_received,
        recoveries                                               as gross_recoveries,
        collection_recovery_fee                                  as recovery_fees,
        out_prncp                                                as outstanding_principal,
        coalesce(hardship_flag = 'Y', false)                     as had_hardship_plan,
        coalesce(debt_settlement_flag = 'Y', false)              as had_debt_settlement

    from source
    -- The source file ends with 33 summary lines ("Total amount funded ...")
    -- that have no loan id. They are footer text, not loans.
    where try_cast(id as bigint) is not null

)

select * from cleaned

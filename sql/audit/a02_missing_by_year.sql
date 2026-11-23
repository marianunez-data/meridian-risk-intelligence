-- Data audit: share of missing values per feature and origination year.
-- Reveals structural missingness (fields that did not exist yet) versus
-- random gaps.
unpivot (
    select
        year(issue_month)                                   as issue_year,
        avg((employment_years is null)::int)                as employment_years,
        avg((debt_to_income is null)::int)                  as debt_to_income,
        avg((revolving_utilization is null)::int)           as revolving_utilization,
        avg((mortgage_accounts is null)::int)               as mortgage_accounts,
        avg((total_current_balance is null)::int)           as total_current_balance,
        avg((bankcard_utilization is null)::int)            as bankcard_utilization,
        avg((months_since_recent_inquiry is null)::int)     as months_since_recent_inquiry,
        avg((months_since_last_delinquency is null)::int)   as months_since_last_delinquency,
        avg((months_since_last_public_record is null)::int) as months_since_last_public_record
    from gold.mart_pd_features
    group by 1
) on columns(* exclude (issue_year)) into name feature value missing_share
order by feature, issue_year;

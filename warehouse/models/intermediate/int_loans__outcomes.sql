-- Silver (business rules): default definition, exposure, loss and the
-- out-of-time split. Every downstream model and notebook uses these columns,
-- so the definition of "bad" exists in exactly one place.

{%- set snapshot = "date '" ~ var('snapshot_date') ~ "'" %}
{%- set window = var('performance_window_months') %}

with loans as (

    select * from {{ ref('stg_lending_club__loans') }}

),

timing as (

    select
        *,
        cast(issue_month + to_months(term_months) as date)                as maturity_month,
        loan_status in ('Charged Off', 'Default')                          as is_defaulted,
        loan_status in ('Fully Paid', 'Charged Off', 'Default')            as is_resolved,
        -- Charge-off happens ~150 days after the last payment received.
        case when loan_status in ('Charged Off', 'Default')
             then cast(coalesce(last_payment_month, issue_month)
                       + to_months({{ var('charge_off_lag_months') }}) as date)
        end                                                                as est_default_month,
        datediff('month', issue_month, {{ snapshot }})                     as months_observed
    from loans

),

flags as (

    select
        *,
        datediff('month', issue_month, est_default_month)                 as months_to_default,
        months_observed >= {{ window }}                                    as has_full_window,
        -- Target: default within the performance window. Only meaningful
        -- when the full window has been observed.
        case when months_observed >= {{ window }}
             then coalesce(is_defaulted
                           and datediff('month', issue_month, est_default_month) <= {{ window }}, false)
        end                                                                as is_bad_24m
    from timing

),

loss as (

    select
        *,
        -- Exposure at default = principal still owed when the loan stopped paying.
        case when is_defaulted then greatest(funded_amount - principal_repaid, 0) end  as exposure_at_default,
        case when is_defaulted then gross_recoveries - recovery_fees end               as net_recoveries,
        case when is_defaulted and funded_amount - principal_repaid > 0
             then least(greatest(1 - (gross_recoveries - recovery_fees)
                                     / (funded_amount - principal_repaid), 0), 1)
        end                                                                            as loss_given_default,
        case when is_defaulted
             then est_default_month <= cast({{ snapshot }}
                  - to_months({{ var('recovery_seasoning_months') }}) as date)
        end                                                                            as has_seasoned_recovery,
        -- Credit conversion factor proxy for amortising loans: share of the
        -- original limit still outstanding at default.
        case when is_defaulted
             then greatest(funded_amount - principal_repaid, 0) / nullif(funded_amount, 0)
        end                                                                            as ead_ratio
    from flags

)

select
    *,
    case
        when year(issue_month) between 2007 and 2014 then 'train'
        when year(issue_month) = 2015                then 'validation'
        when year(issue_month) = 2016                then 'test_oot'
        else 'monitoring'
    end as dataset_split
from loss

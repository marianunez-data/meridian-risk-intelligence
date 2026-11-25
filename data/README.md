# Data

All data is public. The full raw files (about 3.2 GB) are **not stored in this repository**: the Lending Club file alone is 1.6 GB, above GitHub's 100 MB file limit. Instead:

| What | Where | How to get it |
|---|---|---|
| Full raw data | `data/raw/` (git-ignored) | `python scripts/download_data.py` |
| Bronze, warehouse and features | `data/bronze/`, `data/warehouse/`, `data/features/` (git-ignored) | `make bronze warehouse notebooks` |
| Small samples to browse | `data/sample/` (committed) | Open in Excel or pandas |
| App warehouse used by the dashboard | `app/data/meridian_app.duckdb` (committed, 27 MB) | `python scripts/export_app_data.py` |

## Sources

| Dataset | Size | Licence | Link |
|---|---|---|---|
| Lending Club accepted loans, 2007 to 2018 | 2,260,701 loans, 151 columns | Public release | [Hugging Face mirror](https://huggingface.co/datasets/codesignal/lending-club-loan-accepted) |
| PaySim mobile-money simulation | 6,362,620 transactions | CC BY-SA 4.0 | [Hugging Face mirror](https://huggingface.co/datasets/theman10/paysim) |
| FRED macro series (7) | Monthly and quarterly, 1947 onwards | Public domain | [FRED](https://fred.stlouisfed.org/) |
| SEC Financial Statement Data Sets, 2019 Q1 and Q2 | 12,940 filings, 5.9M values | Public domain | [SEC](https://www.sec.gov/dera/data/financial-statement-data-sets) |

## Samples in `data/sample/`

| File | Rows | Content |
|---|---|---|
| `lending_club_sample_10k.csv` | 10,000 | Random loans with the main application fields and the outcome, exactly as delivered by the source |
| `paysim_sample_10k.csv` | 10,000 | Random transactions with the fraud label |
| `supplier_scores.csv` | 1,351 | Altman Z'' score, zone, red flags and risk tier per company (output of notebook 11) |
| `fred_macro_since_2005.csv` | about 6,000 | Long format: series_id, observation_date, value |

## Lending Club sample dictionary

| Column | Meaning |
|---|---|
| `id` | Loan identifier |
| `issue_d` | Month the loan was issued (for example Dec-2015) |
| `loan_amnt`, `funded_amnt` | Amount requested and funded, USD |
| `term` | 36 or 60 months |
| `int_rate` | Interest rate, percent |
| `installment` | Monthly payment, USD |
| `grade`, `sub_grade` | Lending Club's risk grade, A1 (safest) to G5 |
| `emp_length` | Years in current job |
| `home_ownership` | RENT, OWN, MORTGAGE, OTHER |
| `annual_inc` | Self-reported annual income, USD (zero for joint applications; see notebook 02) |
| `verification_status` | Whether Lending Club verified the income |
| `purpose` | Loan purpose stated by the borrower |
| `addr_state` | US state |
| `dti` | Debt payments over income, percent, excluding this loan |
| `fico_range_low`, `fico_range_high` | FICO band at application |
| `earliest_cr_line` | Month the first credit line was opened |
| `inq_last_6mths` | Credit inquiries in the last 6 months |
| `open_acc`, `total_acc` | Open and total credit lines |
| `pub_rec` | Derogatory public records |
| `revol_bal`, `revol_util` | Revolving balance (USD) and utilisation (percent) |
| `mort_acc` | Mortgage accounts |
| `acc_open_past_24mths` | Accounts opened in the last 24 months |
| `bc_util` | Bankcard utilisation, percent |
| `application_type` | Individual or Joint App |
| `loan_status` | Status at the March 2019 snapshot: Fully Paid, Charged Off, Current, Late, Default |
| `total_pymnt`, `recoveries` | Paid and recovered to date. Post-origination: never used as model inputs (notebook 02, leakage audit) |

Full column definitions for every warehouse table are in the dbt project (`make docs` opens the dbt documentation site with the lineage graph).

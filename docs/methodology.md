# Methodology and glossary

This document defines every metric and design decision used in the Meridian Capital Counterparty Risk Intelligence Platform. It is written for stakeholders and is also the knowledge base the AI Risk Analyst searches.

## Default definition (target)

A loan is **bad** if it was charged off within 24 months of its issue date. Lending Club charges off loans at about 150 days past due, so the charge-off month is estimated as the last payment month plus 5 months. The label is only defined for loans observed for at least 24 months before the March 2019 snapshot. Loans issued in 2017 and 2018 have immature outcomes and are used for drift monitoring only. The rule lives in `int_loans__outcomes.sql`.

## Out-of-time split

Train: loans issued 2012 to 2014 (the full-bureau era; bureau attributes did not exist before 2012). Validation: 2015, used for tuning and recalibration. Test: 2016, used once for the final evaluation. Monitoring: 2017 to 2018. Splitting by time mirrors how a model is deployed: built on the past and judged on a future it has not seen.

## Probability of Default (PD)

The probability that a borrower defaults. The scorecard and the challenger predict the 24-month PD. Lifetime PD is obtained by multiplying the 24-month PD by the ratio of lifetime to 24-month defaults observed on 2015 loans (about 1.6 for 36-month loans and 1.8 for 60-month loans).

## Scorecard

A logistic regression on Weight of Evidence (WoE) encoded variables, scaled to points: 600 points equal odds of 50 goods to 1 bad, and every 20 points double the odds (PDO = 20). It has 16 variables covering credit history, capacity, capital, loan conditions and credit-seeking behaviour. It is the benchmark and fallback model.

## Weight of Evidence and Information Value

WoE of a bin = ln(share of goods in the bin / share of bads in the bin). Positive WoE means safer than average. Information Value (IV) = sum of (share of goods - share of bads) x WoE across bins. IV below 0.02 is useless, 0.02 to 0.1 weak, 0.1 to 0.3 medium, above 0.5 suspicious.

## Challenger model

A LightGBM gradient-boosted model with 47 inputs, tuned with Optuna on 2015 validation AUC, with monotonic constraints so that the prediction can only move in the business-logical direction for each numeric input. Probabilities are recalibrated with Platt scaling on 2015 loans. It is the champion model for funding decisions.

## Gini, AUC and KS

AUC is the probability that a randomly chosen bad loan receives a higher risk score than a randomly chosen good loan. Gini = 2 x AUC - 1; banks report Gini. KS is the maximum distance between the cumulative distributions of goods and bads. On the 2016 out-of-time test the challenger reached a Gini of 0.401, the scorecard 0.363 and Lending Club's own sub-grade 0.378.

## SHAP and reason codes

SHAP values decompose each prediction exactly into contributions from each input, in log-odds. The three inputs that raise a borrower's risk the most are the adverse-action reasons shown to declined applicants.

## Loss Given Default (LGD)

The share of the exposure lost after recoveries: 1 - (recoveries - collection fees) / exposure at default. Lending Club's unsecured loans have an LGD of about 90%, almost flat across grades. A downturn LGD of about 94% (the worst observed default year) is used in stress scenarios.

## Exposure at Default (EAD)

The principal still owed when the loan defaults. On average 66% of the original amount for 36-month loans and 80% for 60-month loans, higher than the contractual schedule because borrowers fall behind before charge-off.

## Expected Loss (EL)

EL = PD x LGD x EAD. For the live book, PD is the remaining-life PD conditional on survival so far, and loans already 31 to 120 days late receive a 75% PD. EL is the basis for loss provisions.

## Capital budget simulation (ROI)

Meridian can fund only part of the loan flow. Loans are ranked by expected profit per dollar: the interest margin after funding (2.5%) and servicing (1%) costs, minus expected losses. Realised profit on 2016 loans measures each strategy. At a 50% budget the challenger earned USD 475.0M versus USD 460.2M using Lending Club's grade and USD 279.6M for random selection, with a lower default rate in the funded book.

## Stress testing

Lending Club's history has no usable recession, so macro sensitivity comes from a satellite model on US credit card charge-off rates since 1985: the year-over-year change in log charge-offs is regressed on the change in unemployment. Each extra point of unemployment raises charge-offs by about 18%. Scenarios: baseline 3.9% unemployment, adverse 7.0% (PD multiplier 1.7) and severely adverse 10.0% (multiplier 2.8), applied to defaults expected within a two-year horizon. The stress capital buffer is severely adverse EL minus baseline EL.

## Population Stability Index (PSI) and CSI

PSI = sum of (actual share - expected share) x ln(actual share / expected share) across score bins. Below 0.10 is stable (green), 0.10 to 0.25 needs investigation (amber), above 0.25 requires escalation (red). The Characteristic Stability Index applies the same formula to one input variable. In 2018, tax liens showed the largest drift because the US credit bureaus removed them from credit reports in 2017 and 2018.

## Fraud model and cost-based threshold

Payments fraud is modelled on PaySim transfers and cash-outs with features known at authorisation time, including destination-account velocity. The alert threshold minimises total cost: missed fraud value plus USD 30 per review plus USD 10 friction per false alert (PaySim amounts converted at 100 simulated units = USD 1). The rule engine caught 1% of fraud value in the test period; the restricted model (no balance data) stopped 97%.

## Supplier risk tiers

Altman Z'' = 6.56 x working capital / assets + 3.26 x retained earnings / assets + 6.72 x EBIT / assets + 1.05 x book equity / liabilities. Zones: safe above 2.60, grey 1.10 to 2.60, distress below 1.10. Tiers combine the zone with four red flags (negative operating cash flow, interest cover below 1.5, net loss, current ratio below 1): Tier 1 Low, Tier 2 Watch, Tier 3 High (distress score, at most one red flag), Tier 4 Critical (distress score and two or more red flags).

## Spend at risk

Annual procurement spend with suppliers in Tier 3 or Tier 4. For the illustrative client Atlas Industrial Group it is 28% of spend (USD 229M).

## Data sources and limitations

Lending Club accepted loans 2007 to 2018, FRED macro series, SEC Financial Statement Data Sets (FY2018 10-K filings) and PaySim. Meridian Capital and Atlas Industrial Group are fictional; the procurement ledger is synthetic. The PD models learn from accepted loans only (no reject inference). PaySim is simulated and contains artefacts that make fraud easier to detect than in reality.

# Model card: Meridian PD challenger (LightGBM)

| Field | Value |
|---|---|
| Purpose | Probability that a consumer loan defaults within 24 months of issue; input to funding decisions, pricing and Expected Loss |
| Owner | Credit Risk Analytics (Meridian Capital, fictional) |
| Status | Champion for funding decisions; 16-variable WoE scorecard kept as benchmark and fallback |
| Training data | Lending Club loans issued 2012-01 to 2014-12 (423,810 loans), application-time information only |
| Target | Charge-off within 24 months of issue (estimated charge-off date = last payment + 5 months) |
| Validation | Early stopping and Platt calibration on 2015 loans; one-time out-of-time test on 2016 loans |
| Algorithm | LightGBM gradient boosting, 47 inputs, monotonic constraints on numeric inputs with IV >= 0.02 |
| Out-of-time Gini (2016) | 0.401 (scorecard 0.363, Lending Club grade 0.378) |
| Out-of-time KS (2016) | 0.293 |
| Explainability | Exact TreeSHAP per decision; top 3 positive contributions are the adverse-action reasons |
| Known limitations | Accepted loans only (no reject inference); calibration drifts with the credit cycle; state of residence carries weight and requires fair-lending review |
| Monitoring | Monthly: score PSI, input CSI. Quarterly: Gini and calibration on newly matured quarter, EL versus realised loss by vintage |
| Retraining triggers | PSI > 0.25, Gini < 0.32, or calibration gap > 2 points for two consecutive quarters |

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from lib import ui
from lib.data import models, q

from meridian.economics import LoanEconomics

ui.header("Credit risk", "Credit decision",
          "Score a loan application with both Meridian models. Start from a real 2016 applicant, adjust the key inputs, "
          "and see the default probability, the risk band, the reasons behind the decision and the expected profit.")

M = models()
sample = q("select * from applicant_sample order by loan_id")
loss = q("select * from loss_parameters").set_index("term_months")

PURPOSES = ["debt_consolidation", "credit_card", "home_improvement", "major_purchase", "car", "medical",
            "small_business", "moving", "other"]


def risk_band(score: float, train_cuts=(534, 545, 556, 566, 575, 587)) -> str:
    labels = ["R7 Highest risk", "R6", "R5", "R4", "R3", "R2", "R1 Lowest risk"]
    return labels[int(np.searchsorted(train_cuts, score))]


with st.sidebar:
    st.markdown("**Applicant**")
    if "applicant_idx" not in st.session_state:
        st.session_state.applicant_idx = 42
    if st.button("Load a random 2016 applicant", width="stretch"):
        st.session_state.applicant_idx = int(np.random.default_rng().integers(len(sample)))
    base = sample.iloc[st.session_state.applicant_idx].copy()
    st.caption(f"Loan id {int(base.loan_id)}, issued {pd.Timestamp(base.issue_month):%B %Y}. "
               f"Lending Club grade {base.benchmark_sub_grade}, rate {base.benchmark_interest_rate:.2%}.")

c_in, c_out = st.columns([1, 1.35], gap="large")
with c_in:
    st.subheader("Application inputs")
    a1, a2 = st.columns(2)
    loan = a1.number_input("Loan amount (USD)", 1000, 40000, int(base.loan_amount), step=500)
    term = a2.selectbox("Term", [36, 60], index=0 if int(base.term_months) == 36 else 1, format_func=lambda t: f"{t} months")
    income = a1.number_input("Annual income (USD)", 5000, 1_000_000, int(base.annual_income), step=1000)
    dti = a2.slider("Debt-to-income, excluding this loan (%)", 0.0, 60.0, round(float(min(base.debt_to_income, 0.6)) * 100, 1),
                    0.5, format="%.1f%%") / 100
    fico = a1.slider("FICO score", 660, 850, int(base.fico_score), 1)
    purpose = a2.selectbox("Purpose", PURPOSES, index=PURPOSES.index(str(base.loan_purpose)) if str(base.loan_purpose) in PURPOSES else 0,
                           format_func=lambda p: p.replace("_", " ").capitalize())
    acc24 = a1.slider("Accounts opened, last 24 months", 0, 20, int(base.accounts_opened_24m))
    inq6 = a2.slider("Credit inquiries, last 6 months", 0, 6, int(base.inquiries_6m))
    rate = st.slider("Interest rate offered (%)", 5.0, 31.0, round(float(base.benchmark_interest_rate) * 100, 2), 0.05,
                     format="%.2f%%", help="Defaults to the rate Lending Club charged this applicant.") / 100

app = sample.iloc[[st.session_state.applicant_idx]].copy()
r = rate / 12
installment = loan * r / (1 - (1 + r) ** -term)
app = app.assign(loan_amount=loan, term_months=term, annual_income=income, debt_to_income=dti, fico_score=fico,
                 loan_purpose=purpose, accounts_opened_24m=acc24, inquiries_6m=inq6, installment_amount=installment,
                 loan_to_income=loan / income, payment_to_income=installment * 12 / income)

pd_ch = float(M["challenger"].predict_pd(app)[0])
score = float(M["scorecard"].score(app)[0])
pd_sc = float(M["scorecard"].predict_pd(app)[0])
band = risk_band(score)
life = loss.loc[term]
pd_life = min(pd_ch * life.lifetime_pd_ratio, 0.99)
eco = LoanEconomics(lgd=float(life.lgd_long_run), ead_ratio=float(life.ead_ratio))
exp_profit = float(eco.expected_profit(loan, rate, term, pd_life))
el = pd_life * life.lgd_long_run * life.ead_ratio * loan

with c_out:
    st.subheader("Decision")
    ui.kpi_row([
        ("Probability of default, 24 months", ui.pct(pd_ch), f"Challenger model. Scorecard: {ui.pct(pd_sc)}"),
        ("Scorecard points", f"{score:.0f}", f"Risk band {band}"),
        ("Expected profit", ui.money(exp_profit),
         f"Expected loss {ui.money(el)} over the loan's life"),
    ])
    decision = "Fund" if exp_profit > 0 else "Decline at this price"
    color = ui.GOOD if exp_profit > 0 else ui.CRITICAL
    breakeven = None
    for test_rate in np.arange(0.05, 0.36, 0.0025):
        if eco.expected_profit(loan, test_rate, term, pd_life) > 0:
            breakeven = test_rate
            break
    st.markdown(f'<div class="mc-callout" style="border-left-color:{color}"><b>Recommendation: {decision}.</b> '
                f'At {rate:.2%} the expected interest margin {"covers" if exp_profit > 0 else "does not cover"} the expected '
                f'loss of this applicant. ' + (f'The break-even rate for this risk is about <b>{breakeven:.2%}</b>.' if breakeven else
                'No rate up to 36% covers this risk.') + '</div>', unsafe_allow_html=True)

    contrib = M["challenger"].shap_values(app).iloc[0]
    base_v = contrib.pop("base_value")
    top = contrib.reindex(contrib.abs().sort_values(ascending=False).index).head(8)
    names = [n.replace("_", " ") for n in top.index]
    fig = go.Figure(go.Bar(y=names[::-1], x=top.values[::-1], orientation="h",
                           marker_color=[ui.ORANGE if v > 0 else ui.BLUE for v in top.values[::-1]],
                           hovertemplate="%{y}: %{x:+.3f} log-odds<extra></extra>"))
    fig.add_vline(x=0, line_color=ui.INK_2, line_width=1)
    fig.update_xaxes(title="Contribution to default risk (log-odds); orange raises risk, blue lowers it")
    st.plotly_chart(ui.style_fig(fig, 330, "Why: the eight largest drivers of this prediction (SHAP)"), width="stretch")

st.header("Adverse-action reasons")
r1, r2 = st.columns(2, gap="large")
with r1:
    st.markdown("**Challenger model (SHAP)**")
    for i, rcode in enumerate(M["challenger"].reason_codes(app, top=3)[0], 1):
        st.markdown(f"{i}. {rcode.replace('_', ' ').capitalize()}")
with r2:
    st.markdown("**Scorecard (points lost versus the best bin)**")
    lost = M["scorecard"].points_lost(app).iloc[0].sort_values(ascending=False).head(3)
    for i, (var, pts) in enumerate(lost.items(), 1):
        st.markdown(f"{i}. {var.replace('_', ' ').capitalize()}: {pts:.0f} points below the best bin")

with st.expander("Scorecard points table"):
    st.dataframe(M["points"].assign(variable=lambda d: d.variable.str.replace("_", " ")),
                 hide_index=True, width="stretch",
                 column_config={"woe": st.column_config.NumberColumn("WoE", format="%.3f"),
                                "train_bad_rate": st.column_config.NumberColumn("Bad rate (train)", format="percent"),
                                "train_loans": st.column_config.NumberColumn("Loans (train)", format="%d")})
ui.footer()

import numpy as np
import plotly.graph_objects as go
import streamlit as st
from lib import ui
from lib.data import q

ui.header("Payments", "Fraud monitor",
          "Meridian's mobile wallet (PaySim simulation, converted to USD at 100 units = USD 1). The current rule engine flags "
          "large transfers; the models score every transfer and cash-out at authorisation time.")

by_type = q("select * from mart_fraud_by_type where fraud_transactions > 0")
roi = q("select * from report_fraud_roi_test_period").set_index("model")
fs = q("select * from fraud_scores_test")
th = q("select * from fraud_thresholds").set_index("model").threshold

total_fraud = by_type.fraud_amount.sum()
ui.kpi_row([
    ("Fraud in the simulated month", ui.money(total_fraud), f"{by_type.fraud_transactions.sum():,} cases, transfers and cash-outs only"),
    ("Caught by today's rules", ui.pct(by_type.rule_true_positives.sum() / by_type.fraud_transactions.sum(), 2), "Share of fraud cases, full month"),
    ("Stopped by the restricted model", ui.pct(roi.loc["LightGBM, restricted (no balances)", "fraud_value_caught"] /
                                                  (roi.loc["LightGBM, restricted (no balances)", ["fraud_value_caught", "fraud_value_missed"]].sum())),
     "Share of fraud value, test period"),
    ("Saving vs rule engine", ui.money(roi.loc["LightGBM, restricted (no balances)", "saving_vs_rule_engine"]),
     "14-day test period, net of review cost"),
])

st.header("Hour by hour, test period")
model = st.selectbox("Model", ["LightGBM, restricted (no balances)", "Isolation Forest (no labels)", "LightGBM, full authorisation data"],
                     label_visibility="collapsed")
col = {"LightGBM, restricted (no balances)": "score_restricted", "Isolation Forest (no labels)": "score_iforest",
       "LightGBM, full authorisation data": "score_full"}[model]
fs["alert"] = fs[col] >= th[model]
hourly = fs.groupby("hour_index").apply(lambda g: np.array([g.amount[g.is_fraud].sum(), g.amount[g.is_fraud & g.alert].sum(),
                                                            g.alert.sum()]), include_groups=False)
hourly = np.vstack(hourly.values)
hours = fs.hour_index.unique()
hours.sort()
fig = go.Figure()
fig.add_bar(x=hours, y=hourly[:, 1] / 1e3, name="Fraud value stopped", marker_color=ui.BLUE,
            hovertemplate="Hour %{x}: $%{y:,.0f}K stopped<extra></extra>")
fig.add_bar(x=hours, y=(hourly[:, 0] - hourly[:, 1]) / 1e3, name="Fraud value lost", marker_color=ui.CRITICAL,
            hovertemplate="Hour %{x}: $%{y:,.0f}K lost<extra></extra>")
fig.update_layout(barmode="stack", bargap=0.1)
fig.update_yaxes(tickprefix="$", ticksuffix="K", title="USD")
fig.update_xaxes(title="Simulated hour")
st.plotly_chart(ui.style_fig(fig, 360, f"Fraud value per hour: stopped versus lost ({model})"), width="stretch")

st.subheader("Model comparison, test period")
show = roi[["alerts", "frauds_caught", "fraud_value_caught", "fraud_value_missed", "false_alerts_per_1000_legit",
            "saving_vs_rule_engine"]].reset_index()
for c_ in ["fraud_value_caught", "fraud_value_missed", "saving_vs_rule_engine"]:
    show[c_] = show[c_] / 1e6
st.dataframe(show, hide_index=True, width="stretch", column_config={
    "model": "Model", "alerts": st.column_config.NumberColumn("Alerts", format="%d"),
    "frauds_caught": st.column_config.NumberColumn("Frauds caught", format="%d"),
    "fraud_value_caught": st.column_config.NumberColumn("Stopped (USD M)", format="%.1f"),
    "fraud_value_missed": st.column_config.NumberColumn("Lost (USD M)", format="%.1f"),
    "false_alerts_per_1000_legit": st.column_config.NumberColumn("False alerts / 1,000", format="%.2f"),
    "saving_vs_rule_engine": st.column_config.NumberColumn("Saving vs rules (USD M)", format="%.1f")})
c1, c2 = st.columns([1, 1], gap="large")
with c1:
    st.subheader("Where fraud happens")
    fig = go.Figure(go.Bar(x=by_type.transaction_type.str.replace("_", " "), y=by_type.fraud_amount / 1e6, marker_color=ui.BLUE,
                           customdata=by_type.fraud_rate, hovertemplate="%{x}<br>$%{y:,.1f}M<br>fraud rate %{customdata:.2%}<extra></extra>"))
    fig.update_yaxes(tickprefix="$", ticksuffix="M", title="Fraud value (USD)")
    st.plotly_chart(ui.style_fig(fig, 300), width="stretch")
with c2:
    st.subheader("Reading the results")
    ui.callout("<b>Reading the results honestly.</b> PaySim fraud almost always drains the sender's exact balance, which no "
               "legitimate payment does, so the full model is near perfect and should be read as an upper bound. The restricted "
               "model never sees balances and relies on amount, time of day and the receiving account's history: that is the "
               "planning case. The Isolation Forest needs no fraud labels and suits the first weeks of a new product.")
ui.footer()

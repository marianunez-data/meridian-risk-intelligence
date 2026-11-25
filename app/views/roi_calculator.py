import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from lib import ui
from lib.data import q

from meridian.economics import LoanEconomics

ui.header("Executive", "ROI calculator",
          "Change the business assumptions and see what each risk model is worth. Credit results are recomputed on "
          "434,407 real 2016 loans; fraud results on the 14-day test period. Nothing here is hard-coded.")

tab_credit, tab_fraud = st.tabs(["Credit: capital allocation", "Fraud: alert economics"])

with tab_credit:
    loans = q("select * from roi_loans_2016")
    c1, c2 = st.columns([1, 2.3], gap="large")
    with c1:
        st.subheader("Assumptions")
        budget = st.slider("Capital budget, share of 2016 loan volume", 10, 100, 50, 5, format="%d%%") / 100
        cof = st.slider("Cost of funds, annual", 0.0, 8.0, 2.5, 0.25, format="%.2f%%") / 100
        serv = st.slider("Servicing cost, annual share of balance", 0.0, 3.0, 1.0, 0.25, format="%.2f%%") / 100
        lgd = st.slider("Loss given default", 60, 100, 90, 1, format="%d%%") / 100
        ead = st.slider("Exposure at default, share of principal", 50, 95, 72, 1, format="%d%%") / 100
    eco = LoanEconomics(cost_of_funds=cof, servicing_cost=serv, lgd=lgd, ead_ratio=ead)
    f, r, t, d = loans.funded.values, loans.rate.values, loans.term.values, loans.defaulted.values
    realised = eco.profit(f, r, t, d)
    rng = np.random.default_rng(42)
    keys = {
        "Random selection (no model)": rng.random(len(f)),
        "Highest interest rate first": r + rng.random(len(f)) * 1e-6,
        "Lending Club grade PD": eco.expected_profit(f, r, t, loans.pd_grade.values) / f + rng.random(len(f)) * 1e-9,
        "Meridian scorecard": eco.expected_profit(f, r, t, loans.pd_scorecard.values) / f,
        "Meridian challenger": eco.expected_profit(f, r, t, loans.pd_challenger.values) / f,
    }
    rows = []
    for name, key in keys.items():
        order = np.argsort(-key, kind="stable")
        k = int(np.searchsorted(np.cumsum(f[order]), budget * f.sum())) + 1
        sel = order[:k]
        rows.append({"Strategy": name, "Profit": realised[sel].sum(), "Capital deployed": f[sel].sum(),
                     "Default rate": d[sel].mean()})
    res = pd.DataFrame(rows)
    with c2:
        best = res.set_index("Strategy")
        ui.kpi_row([
            ("Challenger profit", ui.money(best.loc["Meridian challenger", "Profit"]), f"on {ui.money(best.loc['Meridian challenger', 'Capital deployed'])} deployed"),
            ("Uplift vs no model", ui.money(best.loc["Meridian challenger", "Profit"] - best.loc["Random selection (no model)", "Profit"]), "Same capital, model-selected loans"),
            ("Uplift vs Lending Club grade", ui.money(best.loc["Meridian challenger", "Profit"] - best.loc["Lending Club grade PD", "Profit"]),
             f"Default rate {ui.pct(best.loc['Meridian challenger', 'Default rate'])} vs {ui.pct(best.loc['Lending Club grade PD', 'Default rate'])}"),
        ])
        colors = [ui.MUTED, ui.MUTED, ui.ORANGE, ui.AQUA, ui.BLUE]
        fig = go.Figure(go.Bar(x=res.Profit, y=res.Strategy, orientation="h", marker_color=colors,
                               customdata=res["Default rate"],
                               hovertemplate="%{y}<br>Profit %{x:$,.3s}<br>Default rate %{customdata:.1%}<extra></extra>"))
        fig.update_xaxes(tickprefix="$", tickformat="~s", exponentformat="SI", title="Lifetime profit on funded 2016 loans")
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(ui.style_fig(fig, 330, f"Profit by selection strategy at a {budget:.0%} capital budget"), width="stretch")
    ui.callout("<b>How it works.</b> Each strategy ranks the 2016 loans and funds them in order until the budget is used. "
               "Model strategies rank by expected profit per dollar: the interest margin minus PD x LGD x EAD. Profit is then "
               "measured on what actually happened to those loans. The challenger wins at almost every setting because it "
               "finds loans whose price more than pays for their specific risk.")

with tab_fraud:
    fs = q("select * from fraud_scores_test")
    th = q("select * from fraud_thresholds").set_index("model").threshold
    c1, c2 = st.columns([1, 2.3], gap="large")
    with c1:
        st.subheader("Assumptions")
        review = st.number_input("Cost per alert review (USD)", 0, 500, 30, 5)
        friction = st.number_input("Friction cost per false alert (USD)", 0, 500, 10, 5)
        model = st.selectbox("Model", ["LightGBM, restricted (no balances)", "Isolation Forest (no labels)",
                                       "LightGBM, full authorisation data"])
        col = {"LightGBM, restricted (no balances)": "score_restricted", "Isolation Forest (no labels)": "score_iforest",
               "LightGBM, full authorisation data": "score_full"}[model]
        s = fs[col].values
        qs = np.quantile(s, np.linspace(0.80, 0.9999, 300))
        y, a = fs.is_fraud.values, fs.amount.values
        costs = [a[y & (s < t)].sum() + (s >= t).sum() * review + ((s >= t) & ~y).sum() * friction for t in qs]
        opt = qs[int(np.argmin(costs))]
        alert_share = st.slider("Alert rate, share of transactions held (%)", 0.1, 20.0,
                                round(float(max(0.001, (s >= opt).mean())) * 100, 1), 0.1, format="%.1f%%",
                                help="Defaults to the cost-minimising threshold for your assumptions.") / 100
    thr = np.quantile(s, 1 - alert_share)
    flag = s >= thr
    stopped = a[y & flag].sum()
    total_fraud = a[y].sum()
    cost = a[y & ~flag].sum() + flag.sum() * review + (flag & ~y).sum() * friction
    rule_cost = a[y & ~fs.rule_flag.values].sum() + fs.rule_flag.sum() * review
    with c2:
        ui.kpi_row([
            ("Fraud value stopped", ui.pct(stopped / total_fraud), ui.money(stopped)),
            ("Alerts raised", f"{flag.sum():,}", f"{1000 * (flag & ~y).sum() / (~y).sum():.1f} false alerts per 1,000 legitimate"),
            ("Saving vs rule engine", ui.money(rule_cost - cost), "Over the 14-day test period"),
        ])
        grid = np.linspace(0.001, 0.2, 80)
        stop_curve = [a[y & (s >= np.quantile(s, 1 - g))].sum() / total_fraud for g in grid]
        fig = go.Figure(go.Scatter(x=grid, y=stop_curve, line=dict(color=ui.BLUE, width=2.5),
                                   hovertemplate="Alert rate %{x:.1%}<br>Fraud value stopped %{y:.1%}<extra></extra>"))
        fig.add_vline(x=alert_share, line_color=ui.INK_2, line_dash="dash")
        fig.update_xaxes(tickformat=".0%", title="Share of transactions held for review")
        fig.update_yaxes(tickformat=".0%", title="Share of fraud value stopped", range=[0, 1.02])
        st.plotly_chart(ui.style_fig(fig, 330, "Fraud value stopped versus review workload"), width="stretch")
    ui.callout("<b>Note.</b> In the test period legitimate volume collapses while fraud stays constant (a PaySim simulator "
               "artefact), so alert rates here are higher than they would be in production. Use the restricted model as the "
               "planning case; the full model is an upper bound.")
ui.footer()

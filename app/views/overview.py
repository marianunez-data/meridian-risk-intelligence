import plotly.graph_objects as go
import streamlit as st
from lib import ui
from lib.data import headline, q

h = headline()
ui.header("Executive overview", "Counterparty risk at a glance",
          "One view of Meridian's three risk books: consumer lending, mobile payments and client supplier networks. "
          "Every figure below comes from a model validated on data it never saw.")

ui.kpi_row([
    ("Loan book funded", ui.money(h["funded"]), f"{h['loans'] / 1e6:.2f}M loans, 2007 to 2018"),
    ("Live book outstanding", ui.money(h["outstanding"]), "Active loans at March 2019"),
    ("Expected loss provision", ui.money(h["el"]), f"{ui.pct(h['el_rate'])} of outstanding (PD x LGD x EAD)"),
    ("Severe-recession buffer", ui.money(h["stress_buffer"]), "Extra loss if unemployment reaches 10%"),
])
st.write("")
ui.kpi_row([
    ("PD model accuracy (Gini)", f"{h['gini_challenger']:.3f}", f"Lending Club's own grade: {h['gini_lc']:.3f} (2016 out-of-time)"),
    ("Profit uplift, same capital", ui.money(h["profit_challenger"] - h["profit_grade"]),
     f"vs Lending Club grade; {ui.money(h['profit_challenger'] - h['profit_random'])} vs no model"),
    ("Fraud value stopped", ui.pct(h["fraud_stopped_model"], 0), f"Rule engine today: {ui.pct(h['fraud_stopped_rules'], 0)}"),
    ("Client spend at risk", ui.pct(h["spend_at_risk"] / h["spend_total"], 0),
     f"{ui.money(h['spend_at_risk'])} with Tier 3 and 4 suppliers"),
])

st.header("How the loan book evolved")
m = q("""select year(month) as year, sum(funded_amount) funded,
                sum(bad_rate_24m * loans_originated) / sum(loans_originated) filter (where bad_rate_24m is not null) bad
         from mart_portfolio_monthly group by 1 order by 1""")
c1, c2 = st.columns(2, gap="large")
with c1:
    fig = go.Figure(go.Bar(x=m.year, y=m.funded / 1e9, marker_color=ui.BLUE,
                           hovertemplate="%{x}<br>Funded $%{y:,.2f}B<extra></extra>"))
    fig.update_yaxes(tickprefix="$", ticksuffix="B")
    st.plotly_chart(ui.style_fig(fig, 340, "Funded volume by origination year"), width="stretch")
with c2:
    d = m[m.bad.notna() & m.year.between(2009, 2016)]
    fig = go.Figure(go.Scatter(x=d.year, y=d.bad, mode="lines+markers", line=dict(color=ui.ORANGE, width=2.5),
                               hovertemplate="%{x}<br>24-month bad rate %{y:.1%}<extra></extra>"))
    fig.update_yaxes(tickformat=".0%", rangemode="tozero")
    st.plotly_chart(ui.style_fig(fig, 340, "Share of loans defaulting within 24 months (mature years)"), width="stretch")
ui.callout("<b>What this means.</b> Lending grew about ninefold between 2012 and 2016 while the share of loans defaulting "
           "within two years rose from about 8% to over 11%. Underwriting loosened during the growth phase, in the best "
           "economy in a decade. Any model must be judged on these later, riskier borrowers, which is why every result in "
           "this platform is measured out of time.")

st.header("Where the value comes from")
c1, c2, c3 = st.columns(3, gap="large")
with c1:
    st.subheader("Credit decisions")
    st.markdown(f"Funding the half of the 2016 loan flow with the best expected profit earns "
                f"**{ui.money(h['profit_challenger'])}**, versus {ui.money(h['profit_random'])} without a model, and a "
                f"safer book: **{ui.pct(h['dr_challenger'])}** default rate versus {ui.pct(h['dr_grade'])} using "
                f"Lending Club's grade.")
with c2:
    st.subheader("Payments fraud")
    st.markdown(f"The current rule engine stops **{ui.pct(h['fraud_stopped_rules'], 0)}** of fraud value. A model "
                f"using only amount, time and destination-account behaviour stops **{ui.pct(h['fraud_stopped_model'], 0)}**, "
                f"at a review cost that is small by comparison.")
with c3:
    st.subheader("Supplier resilience")
    st.markdown(f"For the client Atlas Industrial Group, **{ui.pct(h['spend_at_risk'] / h['spend_total'], 0)}** of "
                f"annual spend sits with suppliers in the two highest risk tiers. A prioritised action list and a "
                f"supplier-finance offer turn that risk into a managed exposure and a revenue line.")

ui.footer()

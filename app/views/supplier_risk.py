import plotly.graph_objects as go
import streamlit as st
from lib import ui
from lib.data import q

ui.header("Procurement", "Supplier risk",
          "Financial health of 1,351 US public companies that could be a client's suppliers, scored from their FY2018 "
          "annual reports. The client view shows Atlas Industrial Group, a fictional manufacturer with a synthetic spend ledger.")

TIERS = ["Tier 1 Low", "Tier 2 Watch", "Tier 3 High", "Tier 4 Critical"]
sup = q("select * from supplier_scores")
spend = q("select * from procurement_spend")

tab_client, tab_lookup, tab_universe = st.tabs(["Client view: Atlas Industrial Group", "Supplier lookup", "Universe"])

with tab_client:
    total = spend.annual_spend.sum()
    at_risk = spend[spend.risk_tier.isin(TIERS[2:])]
    shares = spend.annual_spend / total
    ui.kpi_row([
        ("Spend under management", ui.money(total), f"{len(spend)} suppliers"),
        ("Spend at risk", ui.money(at_risk.annual_spend.sum()), f"{ui.pct(at_risk.annual_spend.sum() / total, 0)} with Tier 3 and 4 suppliers"),
        ("Critical single-source suppliers", f"{int((spend.single_source & (spend.risk_tier == 'Tier 4 Critical')).sum())}",
         "Qualify a second source now"),
        ("Concentration (HHI)", f"{(shares * 100).pow(2).sum():,.0f}", f"Top 10 suppliers: {ui.pct(shares.nlargest(10).sum(), 0)} of spend"),
    ])
    cat = spend.pivot_table(index="category", columns="risk_tier", values="annual_spend", aggfunc="sum").reindex(columns=TIERS).fillna(0)
    cat = cat.loc[cat.sum(axis=1).sort_values().index]
    fig = go.Figure()
    for t in TIERS:
        fig.add_bar(y=cat.index, x=cat[t], name=t, orientation="h", marker_color=ui.TIER_COLORS[t],
                    marker_line_color="white", marker_line_width=1.5, hovertemplate="%{y}<br>" + t + ": %{x:$,.3s}<extra></extra>")
    fig.update_layout(barmode="stack")
    fig.update_xaxes(tickprefix="$", tickformat="~s", exponentformat="SI")
    st.plotly_chart(ui.style_fig(fig, 360, "Annual spend by category and supplier risk tier"), width="stretch")

    st.subheader("Action list")
    act = at_risk.assign(priority=(at_risk.risk_tier == "Tier 4 Critical").astype(int) * 2 + at_risk.single_source.astype(int)) \
                 .sort_values(["priority", "annual_spend"], ascending=False)
    act["action"] = act.apply(lambda r: "Qualify a second source now; build safety stock" if r.risk_tier == "Tier 4 Critical" and r.single_source
                              else "Shift volume to healthier suppliers" if r.risk_tier == "Tier 4 Critical"
                              else "Cash-flow review; contingency plan" if r.single_source else "Monitor quarterly", axis=1)
    st.dataframe(act[["company_name", "category", "annual_spend", "altman_z_double_prime", "red_flags", "risk_tier", "single_source", "action"]],
                 hide_index=True, width="stretch", height=330, column_config={
                     "company_name": "Supplier", "category": "Category",
                     "annual_spend": st.column_config.NumberColumn("Annual spend", format="dollar"),
                     "altman_z_double_prime": st.column_config.NumberColumn("Altman Z''", format="%.2f"),
                     "red_flags": st.column_config.NumberColumn("Red flags", format="%d"),
                     "risk_tier": "Tier", "single_source": "Single source", "action": "Recommended action"})

    st.subheader("Supplier finance opportunity")
    c1, c2, c3 = st.columns(3)
    uptake = c1.slider("Uptake among Tier 2 suppliers", 0, 100, 40, 5, format="%d%%") / 100
    disc = c2.slider("Early-payment discount", 0.5, 3.0, 1.5, 0.1, format="%.1f%%") / 100
    eligible = spend[spend.risk_tier == "Tier 2 Watch"].annual_spend.sum()
    c3.markdown(ui.kpi("Annual revenue for Meridian", ui.money(eligible * uptake * disc), f"on {ui.money(eligible)} eligible spend"),
                unsafe_allow_html=True)

with tab_lookup:
    name = st.selectbox("Company", sorted(sup.company_name.unique()), index=sorted(sup.company_name.unique()).index("BOEING CO")
                        if "BOEING CO" in set(sup.company_name) else 0)
    s = sup[sup.company_name == name].iloc[0]
    ui.kpi_row([
        ("Altman Z''", f"{s.altman_z_double_prime:.2f}", f"{s.altman_zone} zone"),
        ("Risk tier", s.risk_tier, f"{int(s.red_flags)} of 4 red flags"),
        ("Revenue", ui.money(s.revenue), s.sector_name),
        ("Net margin", ui.pct(s.net_margin) if s.net_margin == s.net_margin else "n/a", f"Current ratio {s.current_ratio:.2f}" if s.current_ratio == s.current_ratio else ""),
    ])
    comps = {"Working capital / assets (x6.56)": 6.56 * s.x1_working_capital_to_assets,
             "Retained earnings / assets (x3.26)": 3.26 * s.x2_retained_earnings_to_assets,
             "EBIT / assets (x6.72)": 6.72 * s.x3_ebit_to_assets,
             "Equity / liabilities (x1.05)": 1.05 * min(s.x4_equity_to_liabilities, 10)}
    fig = go.Figure(go.Bar(x=list(comps.values()), y=list(comps.keys()), orientation="h",
                           marker_color=[ui.BLUE if v >= 0 else ui.CRITICAL for v in comps.values()],
                           hovertemplate="%{y}: %{x:.2f}<extra></extra>"))
    fig.add_vline(x=0, line_color=ui.INK_2, line_width=1)
    st.plotly_chart(ui.style_fig(fig, 280, "Contribution of each ratio to the Z'' score"), width="stretch")
    flags = {"Negative operating cash flow": s.flag_negative_cash_flow, "Interest cover below 1.5": s.flag_low_interest_cover,
             "Net loss": s.flag_net_loss, "Current ratio below 1": s.flag_current_ratio_below_1}
    st.markdown(" &nbsp; ".join(f'<span class="mc-badge"><span class="mc-dot" style="background:{ui.CRITICAL if v else ui.GOOD}"></span>{k}</span>'
                                for k, v in flags.items()), unsafe_allow_html=True)

with tab_universe:
    sectors = sorted(sup.sector_name.unique())
    pick = st.multiselect("Sectors", sectors, default=sectors)
    if not pick:
        st.info("Select at least one sector.")
        st.stop()
    u = sup[sup.sector_name.isin(pick)]
    mix = u.groupby("sector_name").risk_tier.value_counts(normalize=True).unstack().reindex(columns=TIERS).fillna(0)
    fig = go.Figure()
    for t in TIERS:
        fig.add_bar(y=mix.index, x=mix[t], name=t, orientation="h", marker_color=ui.TIER_COLORS[t],
                    marker_line_color="white", marker_line_width=1.5, hovertemplate="%{y}<br>" + t + ": %{x:.0%}<extra></extra>")
    fig.update_layout(barmode="stack")
    fig.update_xaxes(tickformat=".0%")
    st.plotly_chart(ui.style_fig(fig, 380, "Risk tier mix by sector"), width="stretch")
    ui.callout("<b>Method.</b> Altman Z'' (1995) uses four balance-sheet ratios and needs no share price, so it also works for "
               "private suppliers. Tiers combine the Z'' zone with four independent red flags. This corrects known blind spots: "
               "Ford and GM score in the distress zone because their finance arms carry large debts, but healthy cash flows "
               "keep them out of the critical tier.")
ui.footer()

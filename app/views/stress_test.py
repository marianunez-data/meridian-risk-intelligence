import numpy as np
import plotly.graph_objects as go
import streamlit as st
from lib import ui
from lib.data import q

ui.header("Credit risk", "Stress testing",
          "How much would the live loan book lose in a recession? Move the unemployment rate and see expected loss "
          "and the capital buffer update. Sensitivity comes from 35 years of US credit card charge-offs.")

sat = q("select * from stress_satellite").iloc[0]
book = q("""select grade, sum(outstanding) outstanding, sum(expected_loss) el from live_book_el group by 1 order by 1""")
curve = q("select * from stress_curve")
base_el = book.el.sum()
outstanding = book.outstanding.sum()

c1, c2 = st.columns([1, 2.2], gap="large")
with c1:
    st.subheader("Scenario")
    preset = st.radio("Preset", ["Baseline (3.9%)", "Adverse (7.0%)", "Severely adverse (10.0%)", "Custom"], index=2)
    default_u = {"Baseline (3.9%)": 3.9, "Adverse (7.0%)": 7.0, "Severely adverse (10.0%)": 10.0}.get(preset, 8.0)
    u = st.slider("Peak unemployment rate", 3.5, 14.0, default_u, 0.1, format="%.1f%%", disabled=preset != "Custom")
    downturn = st.toggle("Use downturn LGD", value=u > 5.0, help="LGD of the worst observed default year (about 94%).")
    st.caption("The recession multiplier applies to defaults expected within the two-year scenario horizon, computed "
               "loan by loan from each loan's age and term.")
mult = float(np.exp(sat.slope * (u - sat.baseline_unemployment)))
cur = curve[np.isclose(curve.unemployment, round(u, 1))].set_index("grade").reindex(book.grade)
book["stressed"] = (cur.el_downturn if downturn else cur.el_long_run).values
stressed = book.stressed.sum()

with c2:
    ui.kpi_row([
        ("Default-rate multiplier", f"{mult:.2f}x", f"exp({sat.slope:.3f} x {u - sat.baseline_unemployment:+.1f} pts)"),
        ("Stressed expected loss", ui.money(stressed), f"{ui.pct(stressed / outstanding)} of {ui.money(outstanding)} outstanding"),
        ("Capital buffer needed", ui.money(stressed - base_el), "Stressed minus baseline expected loss"),
    ])
    fig = go.Figure()
    fig.add_bar(x=book.grade, y=book.el / book.outstanding, name="Baseline", marker_color=ui.BLUE)
    fig.add_bar(x=book.grade, y=book.stressed / book.outstanding, name=f"Scenario ({u:.1f}% unemployment)", marker_color=ui.ORANGE)
    fig.update_layout(barmode="group", bargap=0.25)
    fig.update_yaxes(tickformat=".0%", title="Expected loss / outstanding")
    fig.update_xaxes(title="Grade")
    st.plotly_chart(ui.style_fig(fig, 360, "Expected loss rate by grade"), width="stretch")

st.header("Why the model uses industry data")
macro = q("select month, unemployment_rate, card_chargeoff_rate from mart_macro_monthly where month >= date '1985-01-01' and month < date '2020-01-01'")
c1, c2 = st.columns(2, gap="large")
with c1:
    fig = go.Figure(go.Scatter(x=macro.month, y=macro.card_chargeoff_rate / 100, line=dict(color=ui.BLUE, width=2),
                               hovertemplate="%{x|%Y-%m}: %{y:.1%}<extra></extra>"))
    for a, b in [("1990-07-01", "1991-03-01"), ("2001-03-01", "2001-11-01"), ("2007-12-01", "2009-06-01")]:
        fig.add_vrect(x0=a, x1=b, fillcolor=ui.GRID, opacity=0.8, line_width=0)
    fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(ui.style_fig(fig, 320, "US credit card charge-off rate (shaded: recessions)"), width="stretch")
with c2:
    fig = go.Figure(go.Scatter(x=macro.month, y=macro.unemployment_rate, line=dict(color=ui.ORANGE, width=2),
                               hovertemplate="%{x|%Y-%m}: %{y:.1f}%<extra></extra>"))
    for a, b in [("1990-07-01", "1991-03-01"), ("2001-03-01", "2001-11-01"), ("2007-12-01", "2009-06-01")]:
        fig.add_vrect(x0=a, x1=b, fillcolor=ui.GRID, opacity=0.8, line_width=0)
    fig.update_yaxes(ticksuffix="%")
    st.plotly_chart(ui.style_fig(fig, 320, "US unemployment rate"), width="stretch")
ui.callout(f"<b>Method.</b> Lending Club's own history contains no usable recession, and its defaults rose while "
           f"unemployment fell (underwriting loosened). The satellite model therefore uses year-over-year changes in US card "
           f"charge-offs since 1985: each extra point of unemployment raises charge-offs by about "
           f"{(np.exp(sat.slope) - 1) * 100:.0f}% (R-squared {sat.r_squared:.2f}). The multiplier is applied to defaults "
           f"expected within the two-year horizon.")
ui.footer()

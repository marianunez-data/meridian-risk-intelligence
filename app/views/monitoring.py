import plotly.graph_objects as go
import streamlit as st
from lib import ui
from lib.data import DOCS, q

ui.header("Model governance", "Model monitoring",
          "Is the PD model still fit for use? Three checks, in the order a model risk committee reads them: does it still "
          "see the same borrowers, does it still rank risk, and are its probabilities still right.")

psi = q("select * from monitoring_psi order by quarter")
csi = q("select * from monitoring_csi order by csi desc")
perf = q("select * from monitoring_performance order by quarter")
latest, lp = psi.iloc[-1], perf.iloc[-1]
gap_status = "Green" if abs(lp.calibration_gap) <= 0.01 else "Amber" if abs(lp.calibration_gap) <= 0.02 else "Red"
gini_status = "Green" if lp.gini_challenger > 0.36 else "Amber" if lp.gini_challenger > 0.32 else "Red"
worst = csi.iloc[0]

c = st.columns(4, gap="small")
for col, (label, value, note, status) in zip(c, [
    ("Score PSI", f"{latest.psi:.3f}", f"{latest.quarter} vs 2012-14 development sample", latest.status),
    ("Worst input CSI", f"{worst.csi:.3f}", worst.variable.replace("_", " "), worst.status),
    ("Gini, latest mature quarter", f"{lp.gini_challenger:.3f}", lp.quarter, gini_status),
    ("Calibration gap", f"{lp.calibration_gap * 100:+.2f} pts", f"Observed minus predicted, {lp.quarter}", gap_status),
]):
    col.markdown(ui.kpi(label, value, f"{note}<br>{ui.status_badge(status)}"), unsafe_allow_html=True)

c1, c2 = st.columns(2, gap="large")
with c1:
    colors = psi.status.map({"Green": ui.GOOD, "Amber": ui.WARNING, "Red": ui.CRITICAL})
    fig = go.Figure(go.Bar(x=psi.quarter, y=psi.psi, marker_color=colors, hovertemplate="%{x}: PSI %{y:.3f}<extra></extra>"))
    fig.add_hline(y=0.10, line_dash="dash", line_color=ui.INK_2, annotation_text="Amber 0.10", annotation_position="top left")
    fig.add_hline(y=0.25, line_dash="dot", line_color=ui.INK_2, annotation_text="Red 0.25", annotation_position="top left")
    fig.update_yaxes(range=[0, 0.3])
    st.plotly_chart(ui.style_fig(fig, 340, "Score stability (PSI) by origination quarter"), width="stretch")
with c2:
    fig = go.Figure()
    for colname, color, name in [("gini_challenger", ui.BLUE, "Challenger"), ("gini_scorecard", ui.AQUA, "Scorecard"),
                                 ("gini_lending_club", ui.ORANGE, "Lending Club grade")]:
        fig.add_scatter(x=perf.quarter, y=perf[colname], name=name, mode="lines+markers", line=dict(color=color, width=2))
    fig.update_yaxes(range=[0.3, 0.45], title="Gini")
    st.plotly_chart(ui.style_fig(fig, 340, "Ranking power by mature quarter"), width="stretch")

c1, c2 = st.columns(2, gap="large")
with c1:
    fig = go.Figure()
    fig.add_scatter(x=perf.quarter, y=perf.observed_bad_rate, name="Observed", mode="lines+markers", line=dict(color=ui.ORANGE, width=2))
    fig.add_scatter(x=perf.quarter, y=perf.predicted_pd, name="Predicted", mode="lines+markers", line=dict(color=ui.BLUE, width=2))
    fig.update_yaxes(tickformat=".1%")
    st.plotly_chart(ui.style_fig(fig, 340, "Calibration: observed versus predicted 24-month bad rate"), width="stretch")
with c2:
    st.markdown("**Inputs that moved most (latest quarter)**")
    show = csi.head(8).assign(variable=lambda d: d.variable.str.replace("_", " "))
    st.dataframe(show[["variable", "csi", "dev_median", "latest_median", "status"]], hide_index=True, width="stretch",
                 height=320, column_config={"variable": "Input", "csi": st.column_config.NumberColumn("CSI", format="%.3f"),
                                            "dev_median": st.column_config.NumberColumn("Median 2012-14", format="%.3f"),
                                            "latest_median": st.column_config.NumberColumn("Median latest", format="%.3f"),
                                            "status": "Status"})
ui.callout("<b>What monitoring caught.</b> Tax liens drifted the most, not because borrowers changed but because the US credit "
           "bureaus removed tax liens from credit reports in 2017 and 2018. Utilisation and FICO shifted because Lending Club "
           "tightened its policy. The score itself stayed stable and kept ranking risk, so the right response is quarterly "
           "recalibration, not a rebuild.")

with st.expander("Model card"):
    st.markdown((DOCS / "model_card_pd.md").read_text())
ui.footer()

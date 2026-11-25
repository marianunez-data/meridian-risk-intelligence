import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from lib import ui
from lib.data import q

ui.header("Credit risk", "Portfolio and vintages",
          "Explore the loan book by year, grade, term and geography. Vintage curves show how fast each cohort of loans "
          "defaulted, the view a credit committee uses to spot deteriorating underwriting early.")

with st.sidebar:
    st.markdown("**Filters**")
    years = st.slider("Origination years", 2007, 2018, (2012, 2018))
    grades = st.multiselect("Grades", list("ABCDEFG"), default=list("ABCDEFG"))
    terms = st.multiselect("Term (months)", [36, 60], default=[36, 60])

if not grades or not terms:
    st.info("Select at least one grade and one term.")
    st.stop()

where = (f"year(issue_month) between {years[0]} and {years[1]} and grade in ({','.join(repr(g) for g in grades)}) "
         f"and term_months in ({','.join(str(t) for t in terms)})")
k = q(f"""select sum(loans) loans, sum(funded_amount) funded, sum(rate_x_funded) / sum(funded_amount) rate,
                 sum(bad_24m) / nullif(sum(loans_with_24m_outcome), 0) bad24, sum(realised_loss) loss
          from portfolio_cube where {where}""").iloc[0]
ui.kpi_row([
    ("Loans", f"{k.loans:,.0f}", f"{years[0]} to {years[1]}"),
    ("Funded", ui.money(k.funded), "Total principal lent"),
    ("Weighted interest rate", ui.pct(k.rate, 2), "Funding-weighted"),
    ("24-month bad rate", ui.pct(k.bad24), "Loans with a mature outcome"),
    ("Realised credit loss", ui.money(k.loss), "Exposure at default minus recoveries"),
])

st.header("Vintage curves")
vterm = st.radio("Loan term for vintage curves", [36, 60], horizontal=True, format_func=lambda t: f"{t}-month loans")
vc = q(f"""select vintage_year, months_on_book, sum(cumulative_defaults) / sum(loans) cdr
           from mart_vintage_curves
           where vintage_year between {max(years[0], 2009)} and {years[1]} and term_months = {vterm}
           group by all order by all""")
vys = sorted(vc.vintage_year.unique())
ramp = ui.SEQ_BLUE[-len(vys):] if len(vys) <= len(ui.SEQ_BLUE) else px.colors.sample_colorscale("Blues", len(vys), low=0.3)
fig = go.Figure()
for color, y in zip(ramp, vys):
    d = vc[vc.vintage_year == y]
    fig.add_trace(go.Scatter(x=d.months_on_book, y=d.cdr, name=str(y), mode="lines", line=dict(color=color, width=2),
                             hovertemplate=f"{y}: month %{{x}}<br>cumulative default %{{y:.1%}}<extra></extra>"))
fig.update_yaxes(tickformat=".0%", title="Cumulative default rate")
fig.update_xaxes(title="Months on book")
st.plotly_chart(ui.style_fig(fig, 400, "Cumulative default rate by vintage (darker = more recent)"), width="stretch")
ui.callout("<b>How to read it.</b> Each line is the cohort of loans issued in one year. A line that rises faster than "
           "older ones signals weaker underwriting. From 2013 to 2016 each vintage defaulted faster than the previous "
           "one; 2017 and 2018 track 2016 closely.")

c1, c2 = st.columns(2, gap="large")
with c1:
    mix = q(f"""select year(issue_month) yr, grade, sum(funded_amount) funded from portfolio_cube
                where {where} group by all order by all""")
    mix["share"] = mix.funded / mix.groupby("yr").funded.transform("sum")
    fig = px.bar(mix, x="yr", y="share", color="grade", labels={"grade": ""}, color_discrete_sequence=ui.SEQ_BLUE[::-1] + ["#08254a"],
                 category_orders={"grade": list("ABCDEFG")})
    fig.update_traces(marker_line_color="white", marker_line_width=1,
                      hovertemplate="%{x} grade %{fullData.name}: %{y:.1%}<extra></extra>")
    fig.update_yaxes(tickformat=".0%", title=None)
    fig.update_xaxes(title=None, dtick=1)
    st.plotly_chart(ui.style_fig(fig, 380, "Grade mix by origination year"), width="stretch")
with c2:
    pr = q(f"""select loan_purpose, sum(loans) loans, sum(bad_24m) / nullif(sum(loans_with_24m_outcome), 0) bad
               from portfolio_cube where {where} group by 1 having sum(loans_with_24m_outcome) > 500 order by bad""")
    fig = go.Figure(go.Bar(y=pr.loan_purpose.str.replace("_", " "), x=pr.bad, orientation="h", marker_color=ui.BLUE,
                           customdata=pr.loans, hovertemplate="%{y}: %{x:.1%} (%{customdata:,} loans)<extra></extra>"))
    fig.update_xaxes(tickformat=".0%")
    st.plotly_chart(ui.style_fig(fig, 380, "24-month bad rate by loan purpose"), width="stretch")

st.header("Geography")
geo = q(f"""select state_code, sum(funded_amount) / 1e6 funded, sum(bad_24m) / nullif(sum(loans_with_24m_outcome), 0) bad
            from portfolio_cube where {where} group by 1""")
metric = st.radio("Show", ["Funded amount", "24-month bad rate"], horizontal=True, label_visibility="collapsed")
col = "funded" if metric == "Funded amount" else "bad"
fig = px.choropleth(geo, locations="state_code", locationmode="USA-states", color=col, scope="usa",
                    color_continuous_scale=[[0, ui.SEQ_BLUE[0]], [1, ui.SEQ_BLUE[-1]]],
                    labels={"funded": "Funded", "bad": "Bad rate"})
fig.update_traces(hovertemplate="%{location}: " + ("$%{z:,.0f}M" if col == "funded" else "%{z:.1%}") + "<extra></extra>")
fig.update_layout(coloraxis_colorbar=dict(tickprefix="$" if col == "funded" else "", ticksuffix="M" if col == "funded" else "",
                                          tickformat=",.0f" if col == "funded" else ".0%", title=None, thickness=12),
                  geo=dict(bgcolor="rgba(0,0,0,0)", lakecolor="white"))
st.plotly_chart(ui.style_fig(fig, 430, f"{metric} by state"), width="stretch")
ui.footer()

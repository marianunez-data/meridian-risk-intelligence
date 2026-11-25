"""Presentation layer: typography, KPI cards, section headers and the Plotly theme."""
from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

INK, INK_2, MUTED = "#0b0b0b", "#52514e", "#8a8984"
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
GOOD, WARNING, SERIOUS, CRITICAL = "#0ca30c", "#fab219", "#ec835a", "#d03b3b"
GRID, BORDER, SURFACE = "#e7e6e2", "#e2e1dc", "#ffffff"
SEQ_BLUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
TIER_COLORS = {"Tier 1 Low": GOOD, "Tier 2 Watch": WARNING, "Tier 3 High": SERIOUS, "Tier 4 Critical": CRITICAL}

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"], .stMarkdown, .stText, button, input, textarea, select {{
    font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif !important;
}}
.block-container {{ padding-top: 4.5rem; padding-bottom: 3rem; max-width: 1320px; }}
h1, h2, h3 {{ letter-spacing: -0.01em; color: {INK}; }}
h1 {{ font-size: 1.85rem !important; font-weight: 700 !important; margin-bottom: 0.1rem !important; }}
h2 {{ font-size: 1.25rem !important; font-weight: 600 !important; margin-top: 1.6rem !important; }}
h3 {{ font-size: 1.02rem !important; font-weight: 600 !important; }}
.mc-eyebrow {{ text-transform: uppercase; letter-spacing: 0.08em; font-size: 0.72rem; font-weight: 600; color: {BLUE};
               margin-bottom: 0.15rem; }}
.mc-lede {{ color: {INK_2}; font-size: 1.0rem; line-height: 1.55; max-width: 920px; margin: 0.2rem 0 1.1rem 0; }}
.mc-card {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 10px; padding: 14px 16px 12px 16px;
            height: 100%; min-height: 128px; }}
.mc-card .label {{ font-size: 0.74rem; text-transform: uppercase; letter-spacing: 0.06em; color: {MUTED}; font-weight: 600; }}
.mc-card .value {{ font-size: 1.65rem; font-weight: 700; color: {INK}; line-height: 1.25; margin-top: 4px;
                   font-variant-numeric: tabular-nums; }}
.mc-card .note {{ font-size: 0.80rem; color: {INK_2}; margin-top: 4px; line-height: 1.35; }}
.mc-callout {{ border-left: 3px solid {BLUE}; background: #f3f7fd; padding: 12px 16px; border-radius: 0 8px 8px 0;
               color: {INK}; font-size: 0.92rem; line-height: 1.5; margin: 0.4rem 0 1rem 0; }}
.mc-callout b {{ font-weight: 600; }}
.mc-badge {{ display: inline-block; padding: 2px 9px; border-radius: 999px; font-size: 0.76rem; font-weight: 600;
             border: 1px solid {BORDER}; color: {INK}; background: {SURFACE}; }}
.mc-dot {{ display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 6px; vertical-align: 0; }}
.mc-footer {{ color: {MUTED}; font-size: 0.75rem; margin-top: 2.5rem; border-top: 1px solid {BORDER}; padding-top: 0.8rem; }}
section[data-testid="stSidebar"] {{ border-right: 1px solid {BORDER}; }}
[data-testid="stSidebarHeader"] img, [data-testid="stLogo"] {{ height: 2.6rem !important; max-width: 100% !important; }}
section[data-testid="stSidebar"] .mc-brand {{ font-weight: 700; font-size: 1.05rem; color: {INK}; letter-spacing: -0.01em; }}
section[data-testid="stSidebar"] .mc-sub {{ color: {MUTED}; font-size: 0.78rem; margin-bottom: 0.6rem; }}
div[data-testid="stMetric"] {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 10px; padding: 10px 14px; }}
.stTabs [data-baseweb="tab"] {{ font-weight: 500; }}
</style>
"""


def setup_page() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    pio.templates["meridian"] = go.layout.Template(layout=dict(
        font=dict(family="Inter, Helvetica Neue, Arial, sans-serif", size=13, color=INK),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        colorway=[BLUE, ORANGE, AQUA, YELLOW, "#e87ba4", "#008300", "#6250d6", "#e34948"],
        margin=dict(l=8, r=8, t=48, b=8),
        title=dict(x=0, xanchor="left", font=dict(size=15, color=INK)),
        xaxis=dict(showgrid=False, linecolor="#b9b8b2", ticks="outside", tickcolor="#b9b8b2", tickfont=dict(color=INK_2),
                   title=dict(font=dict(color=INK_2, size=12))),
        yaxis=dict(gridcolor=GRID, zeroline=False, tickfont=dict(color=INK_2), title=dict(font=dict(color=INK_2, size=12))),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0, font=dict(color=INK_2, size=12), title_text=""),
        hoverlabel=dict(bgcolor="white", bordercolor=GRID, font=dict(color=INK, size=12)),
    ))
    pio.templates.default = "meridian"


def header(eyebrow: str, title: str, lede: str) -> None:
    st.markdown(f'<div class="mc-eyebrow">{eyebrow}</div>', unsafe_allow_html=True)
    st.title(title)
    st.markdown(f'<div class="mc-lede">{lede}</div>', unsafe_allow_html=True)


def kpi(label: str, value: str, note: str = "") -> str:
    return f'<div class="mc-card"><div class="label">{label}</div><div class="value">{value}</div><div class="note">{note}</div></div>'


def kpi_row(cards: list[tuple[str, str, str]]) -> None:
    cols = st.columns(len(cards), gap="small")
    for col, (label, value, note) in zip(cols, cards):
        col.markdown(kpi(label, value, note), unsafe_allow_html=True)


def callout(text: str) -> None:
    st.markdown(f'<div class="mc-callout">{text}</div>', unsafe_allow_html=True)


def status_badge(status: str) -> str:
    color = {"Green": GOOD, "Amber": WARNING, "Red": CRITICAL}.get(status, MUTED)
    return f'<span class="mc-badge"><span class="mc-dot" style="background:{color}"></span>{status}</span>'


def footer() -> None:
    st.markdown('<div class="mc-footer">Meridian Capital is a fictional company. Data: Lending Club loans 2007-2018, '
                'FRED, SEC Financial Statement Data Sets (FY2018), PaySim. Figures are illustrative of the methods, '
                'not statements about any real company.</div>', unsafe_allow_html=True)


def money(v: float, unit: str = "auto", cur: str = "$") -> str:
    if v < 0:
        return "-" + money(-v, unit, cur)
    a = abs(v)
    if unit == "auto" and a < 10_000:
        return f"{cur}{v:,.0f}"
    if unit == "B" or (unit == "auto" and a >= 1e9):
        return f"{cur}{v / 1e9:,.2f}B"
    if unit == "M" or (unit == "auto" and a >= 1e6):
        return f"{cur}{v / 1e6:,.1f}M"
    if unit == "K" or (unit == "auto" and a >= 1e3):
        return f"{cur}{v / 1e3:,.0f}K"
    return f"{cur}{v:,.0f}"


def pct(v: float, d: int = 1) -> str:
    return f"{v * 100:.{d}f}%"


def style_fig(fig: go.Figure, height: int = 380, title: str | None = None) -> go.Figure:
    fig.update_layout(height=height, title=title)
    return fig

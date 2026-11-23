"""House chart style for notebooks (matplotlib) and the app (plotly).

One palette, one type scale, one grid treatment, so every figure in the
project reads as part of the same system. Colours come from a validated,
colour-vision-deficiency-safe categorical order; status colours are reserved
for good / warning / critical states and never used as series colours.
"""
from __future__ import annotations

import matplotlib as mpl
from matplotlib.ticker import FuncFormatter

# Categorical (fixed order, never cycled past what a chart needs)
BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED = (
    "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948",
)
SERIES = [BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED]

# Sequential blue ramp (light -> dark) for magnitude
SEQ_BLUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

# Status (reserved)
GOOD, WARNING, SERIOUS, CRITICAL = "#0ca30c", "#fab219", "#ec835a", "#d03b3b"

# Ink and surfaces
INK, INK_2, INK_MUTED = "#0b0b0b", "#52514e", "#8a8984"
SURFACE, GRID, NEUTRAL = "#fcfcfb", "#e7e6e2", "#b9b8b2"
FONT = "DejaVu Sans"


def set_style() -> None:
    """Apply the house style to matplotlib globally."""
    mpl.rcParams.update({
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "figure.dpi": 110,
        "savefig.dpi": 160,
        "figure.figsize": (10, 4.6),
        "font.family": FONT,
        "font.size": 10,
        "text.color": INK,
        "axes.labelcolor": INK_2,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.titlepad": 26,
        "axes.labelsize": 10,
        "axes.edgecolor": NEUTRAL,
        "axes.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "axes.axisbelow": True,
        "axes.prop_cycle": mpl.cycler(color=SERIES),
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "xtick.color": INK_2,
        "ytick.color": INK_2,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.frameon": False,
        "legend.fontsize": 9,
        "lines.linewidth": 2,
        "lines.markersize": 6,
        "patch.linewidth": 0,
    })


def subtitle(ax, text: str) -> None:
    """Grey one-line takeaway under the bold title."""
    ax.annotate(text, (0, 1), xycoords="axes fraction", xytext=(0, 7), textcoords="offset points",
                fontsize=9.5, color=INK_2, va="bottom", ha="left")


def source(fig, text: str, y: float = -0.02) -> None:
    fig.text(0.01, y, f"Source: {text}", fontsize=8, color=INK_MUTED, ha="left", va="top")


def label_line_ends(ax, items, min_gap: float, x_pad: float = 0.6) -> None:
    """Direct-label line ends, nudging labels apart so they never overlap.

    items: list of (x, y, text). min_gap is in data units of the y axis.
    """
    items = sorted(items, key=lambda t: t[1])
    placed = []
    for x, y, text in items:
        if placed and y - placed[-1] < min_gap:
            y = placed[-1] + min_gap
        placed.append(y)
        ax.text(x + x_pad, y, text, fontsize=9, va="center", color=INK_2)


def pct(ax, axis: str = "y", decimals: int = 0) -> None:
    fmt = FuncFormatter(lambda v, _: f"{v:.{decimals}%}")
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(fmt)


def money(ax, axis: str = "y", unit: str = "B") -> None:
    scale = {"B": 1e9, "M": 1e6, "K": 1e3}[unit]
    fmt = FuncFormatter(lambda v, _: f"${v / scale:,.1f}{unit}" if unit == "B" else f"${v / scale:,.0f}{unit}")
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(fmt)


def plotly_template() -> dict:
    """Plotly layout template matching the matplotlib style (used by the app)."""
    return dict(
        layout=dict(
            font=dict(family="Inter, Helvetica, Arial, sans-serif", size=13, color=INK),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            colorway=SERIES,
            margin=dict(l=10, r=10, t=40, b=10),
            xaxis=dict(showgrid=False, linecolor=NEUTRAL, tickfont=dict(color=INK_2), zeroline=False),
            yaxis=dict(gridcolor=GRID, zeroline=False, tickfont=dict(color=INK_2)),
            legend=dict(orientation="h", y=1.08, x=0, font=dict(color=INK_2)),
            hoverlabel=dict(bgcolor="white", bordercolor=GRID, font=dict(color=INK)),
            title=dict(x=0, xanchor="left", font=dict(size=15)),
        )
    )

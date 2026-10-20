"""Performance metrics, charts and the QuantStats tearsheet."""

import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import quantstats as qs

# QuantStats asks for Arial, which many systems lack; silence the font fallback noise.
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)


def summary_table(returns_by_strategy, periods_per_year, risk_free_rate):
    rows = {}
    for name, r in returns_by_strategy.items():
        rows[name] = {
            "CAGR": qs.stats.cagr(r, rf=0, periods=periods_per_year),
            "Volatility": qs.stats.volatility(r, periods=periods_per_year),
            "Sharpe": qs.stats.sharpe(r, rf=risk_free_rate, periods=periods_per_year),
            "Sortino": qs.stats.sortino(r, rf=risk_free_rate, periods=periods_per_year),
            "Max Drawdown": qs.stats.max_drawdown(r),
            "Calmar": qs.stats.calmar(r, periods=periods_per_year),
        }
    return pd.DataFrame(rows).T


def plot_growth(returns_by_strategy, path, title):
    fig, ax = plt.subplots(figsize=(10, 5.5))
    for name, r in returns_by_strategy.items():
        growth = 10_000 * (1 + r).cumprod()
        style = "--" if "benchmark" in name.lower() else "-"
        ax.plot(growth.index, growth.values, style, linewidth=1.8, label=name)
    ax.set_title(title, fontsize=13, loc="left")
    ax.set_ylabel("Value of $10,000 (CAD)")
    ax.grid(alpha=0.25)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_weights(portfolios, path):
    weights = pd.DataFrame(portfolios).fillna(0).T
    fig, ax = plt.subplots(figsize=(10, 4.5))
    weights.plot(kind="barh", stacked=True, ax=ax, width=0.65, colormap="tab10")
    ax.set_xlabel("Portfolio weight")
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.set_title("Allocation by strategy (estimated on training window)", fontsize=13, loc="left")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(ncol=4, frameon=False, bbox_to_anchor=(0, -0.18), loc="upper left")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def tearsheet(returns, benchmark, path, title, periods_per_year, risk_free_rate):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    qs.reports.html(
        returns, benchmark=benchmark, rf=risk_free_rate, title=title,
        output=str(path), periods_per_year=periods_per_year,
    )

"""Portfolio Performance Analyzer.

Estimates portfolio weights on a training window, then tests every strategy
out-of-sample against a benchmark and writes charts plus a QuantStats tearsheet.

Examples
--------
    # Live data from Yahoo Finance
    python analyze.py

    # Offline, using the bundled sample data
    python analyze.py --csv data/weekly_prices_cad_etfs.csv
"""

import argparse
from pathlib import Path

import pandas as pd

from portfolio_analyzer.data import PERIODS_PER_YEAR, load_prices, save_prices
from portfolio_analyzer.optimize import build_portfolios, portfolio_returns
from portfolio_analyzer.report import plot_growth, plot_weights, summary_table, tearsheet

DEFAULT_TICKERS = ["ZSP.TO", "XIU.TO", "XEF.TO", "XEC.TO", "ZAG.TO", "XRE.TO", "CGL.TO"]


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--tickers", nargs="+", default=DEFAULT_TICKERS, help="ETFs or stocks to allocate across")
    p.add_argument("--benchmark", default="XIU.TO", help="Benchmark ticker (default: TSX 60 ETF)")
    p.add_argument("--start", default="2013-05-01", help="Start of the training window")
    p.add_argument("--split", default="2021-12-31", help="Last date of the training window; testing starts after it")
    p.add_argument("--end", default=None, help="End of the test window (default: latest)")
    p.add_argument("--frequency", choices=PERIODS_PER_YEAR, default="weekly")
    p.add_argument("--risk-free", type=float, default=0.03, help="Annual risk-free rate")
    p.add_argument("--max-weight", type=float, default=0.35, help="Cap on any single holding")
    p.add_argument("--csv", default=None, help="Read prices from this CSV instead of downloading")
    p.add_argument("--out", default="reports", help="Output folder")
    return p.parse_args()


def main():
    args = parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    periods = PERIODS_PER_YEAR[args.frequency]

    universe = list(dict.fromkeys(args.tickers + [args.benchmark]))
    prices = load_prices(universe, args.start, args.end, args.frequency, args.csv)
    if not args.csv:
        save_prices(prices, out / "prices.csv")

    train = prices.loc[: args.split, args.tickers]
    test = prices.loc[args.split :]
    print(f"Training: {train.index[0]:%Y-%m-%d} to {train.index[-1]:%Y-%m-%d} ({len(train)} periods)")
    print(f"Testing:  {test.index[0]:%Y-%m-%d} to {test.index[-1]:%Y-%m-%d} ({len(test)} periods)\n")

    portfolios = build_portfolios(train, periods, args.risk_free, args.max_weight)

    test_returns = {name: portfolio_returns(test, w) for name, w in portfolios.items()}
    benchmark_returns = test[args.benchmark].pct_change().dropna()
    test_returns[f"{args.benchmark} (benchmark)"] = benchmark_returns

    weights_table = pd.DataFrame(portfolios).fillna(0).rename_axis("ticker")
    weights_table.round(4).to_csv(out / "weights.csv")

    metrics = summary_table(test_returns, periods, args.risk_free)
    metrics.round(4).to_csv(out / "out_of_sample_metrics.csv")

    plot_growth(test_returns, out / "growth_out_of_sample.png",
                f"Growth of $10,000, out-of-sample ({test.index[0]:%b %Y} to {test.index[-1]:%b %Y})")
    plot_weights(portfolios, out / "weights.png")

    best = metrics.drop(index=f"{args.benchmark} (benchmark)")["Sharpe"].idxmax()
    tearsheet(test_returns[best], benchmark_returns, out / "tearsheet.html",
              f"{best} portfolio vs {args.benchmark} (out-of-sample)", periods, args.risk_free)

    fmt = {"CAGR": "{:.1%}", "Volatility": "{:.1%}", "Max Drawdown": "{:.1%}",
           "Sharpe": "{:.2f}", "Sortino": "{:.2f}", "Calmar": "{:.2f}"}
    print("Weights (training window):")
    print(weights_table.map(lambda v: f"{v:.0%}" if v else "-").to_string(), "\n")
    print("Out-of-sample performance:")
    print(metrics.apply(lambda col: col.map(fmt[col.name].format)).to_string())
    print(f"\nBest risk-adjusted strategy: {best}. Reports saved to {out.resolve()}")


if __name__ == "__main__":
    main()

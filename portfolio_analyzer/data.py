"""Load ETF price data, either live from Yahoo Finance or from a local CSV."""

from pathlib import Path

import pandas as pd

PERIODS_PER_YEAR = {"daily": 252, "weekly": 52}


def load_prices(tickers, start, end=None, frequency="weekly", csv_path=None):
    """Return a DataFrame of adjusted close prices, one column per ticker.

    If csv_path is given, prices are read from that file (columns = tickers,
    index = date). Otherwise they are downloaded with yfinance.
    """
    if csv_path:
        prices = pd.read_csv(csv_path, index_col=0, parse_dates=True)
        missing = set(tickers) - set(prices.columns)
        if missing:
            raise ValueError(f"Tickers not found in {csv_path}: {sorted(missing)}")
        prices = prices[tickers]
    else:
        prices = _download(tickers, start, end, frequency)

    prices = prices.loc[start:end].dropna()
    if prices.empty:
        raise ValueError("No overlapping price history for these tickers and dates.")
    return prices


def _download(tickers, start, end, frequency):
    import yfinance as yf

    interval = {"daily": "1d", "weekly": "1wk"}[frequency]
    raw = yf.download(
        tickers, start=start, end=end, interval=interval,
        auto_adjust=True, progress=False,
    )
    if raw.empty:
        raise RuntimeError("Yahoo Finance returned no data. Check tickers and your connection.")
    prices = raw["Close"]
    if isinstance(prices, pd.Series):
        prices = prices.to_frame(tickers[0])
    return prices[tickers]


def save_prices(prices, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    prices.round(4).to_csv(path, index_label="date")

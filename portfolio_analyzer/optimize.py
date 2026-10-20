"""Build portfolio weights with several approaches using PyPortfolioOpt."""

import pandas as pd
import scipy.cluster.hierarchy as sch
from pypfopt import EfficientFrontier, HRPOpt, expected_returns, risk_models

# PyPortfolioOpt 1.6 validates the HRP linkage method against a private SciPy
# attribute that SciPy 1.18 removed, so HRPOpt.optimize() crashes.
# Upstream issue: https://github.com/PyPortfolio/PyPortfolioOpt/issues/754
# Restore the attribute until a fixed release is out.
if not hasattr(sch, "_LINKAGE_METHODS"):
    sch._LINKAGE_METHODS = {
        "single": 0, "complete": 1, "average": 2, "centroid": 3,
        "median": 4, "ward": 5, "weighted": 6,
    }


def build_portfolios(prices, periods_per_year, risk_free_rate=0.03, max_weight=0.35):
    """Return a dict of {strategy name: pd.Series of weights}.

    Weights are estimated only from the prices passed in, so pass the
    training window to keep the backtest free of look-ahead bias.
    """
    mu = expected_returns.mean_historical_return(prices, frequency=periods_per_year)
    cov = risk_models.CovarianceShrinkage(prices, frequency=periods_per_year).ledoit_wolf()
    bounds = (0, max_weight)

    portfolios = {}

    ef = EfficientFrontier(mu, cov, weight_bounds=bounds)
    ef.max_sharpe(risk_free_rate=risk_free_rate)
    portfolios["Max Sharpe"] = pd.Series(ef.clean_weights())

    ef = EfficientFrontier(mu, cov, weight_bounds=bounds)
    ef.min_volatility()
    portfolios["Min Volatility"] = pd.Series(ef.clean_weights())

    returns = prices.pct_change().dropna()
    hrp = HRPOpt(returns)
    hrp.optimize()
    portfolios["Hierarchical Risk Parity"] = pd.Series(hrp.clean_weights())

    n = prices.shape[1]
    portfolios["Equal Weight"] = pd.Series(1 / n, index=prices.columns)

    return {name: w[w > 0].sort_values(ascending=False) for name, w in portfolios.items()}


def portfolio_returns(prices, weights):
    """Periodic returns of a portfolio rebalanced back to target weights each period."""
    returns = prices[weights.index].pct_change().dropna()
    return returns.mul(weights, axis=1).sum(axis=1)

"""
fundamentals.py
---------------
Step 2 tool (Lab 1): live fundamental ratios via financetoolkit (FMP API).

Mirrors the book's `get_company_fundamentals` tool: profitability, valuation
and liquidity ratios for a given ticker, fetched live from the Financial
Modeling Prep API through the financetoolkit `Toolkit` wrapper.

Return type note: the book's version returns dict[str, pd.DataFrame], but
DataFrames are not JSON-serializable and cannot cross the SDK's function-tool
bridge cleanly. We return the same numbers as JSON text (the same convention
the Chapter 4 tools use) so the model can reason over them.

The financetoolkit / pandas imports happen lazily inside the function: that
way `main.py list` still works even when the heavy data libs are missing.
"""

from __future__ import annotations

import json

from agents import function_tool

from core.config import require

# Ratio subsets kept from the full set that `collect_all_ratios` returns.
PROFITABILITY_RATIOS = [
    "Return on Equity",
    "Return on Assets",
    "Gross Margin",
    "Operating Margin",
    "Net Profit Margin",
]

VALUATION_RATIOS = [
    "Price-to-Earnings",
    "Price-to-Book",
    "Price-to-Cash-Flow",
    "Price-to-Free-Cash-Flow",
    "EV-to-EBITDA",
    "EV-to-Sales",
]

LIQUIDITY_RATIOS = [
    "Current Ratio",
    "Quick Ratio",
    "Cash Ratio",
    "Working Capital",
    "Operating Cash Flow Ratio",
    "Operating Cash Flow to Sales Ratio",
    "Short Term Coverage Ratio",
]


@function_tool
def get_company_fundamentals(ticker: str) -> str:
    """
    Get profitability, valuation and liquidity fundamental ratios for a stock.

    Fetch live ratio data for a company from the Financial Modeling Prep API.
    Useful whenever the user asks about a company's performance, margins,
    valuation multiples (P/E, P/B, EV/EBITDA) or short-term liquidity.

    Args:
        ticker: Stock ticker symbol, e.g. 'AAPL', 'MSFT', 'TSLA'.
    """
    from financetoolkit import Toolkit

    api_key = require("FINANCIAL_MODELING_PREP_API_KEY")
    toolkit = Toolkit([ticker], api_key=api_key, start_date="2022-01-01")
    ratios = toolkit.ratios.collect_all_ratios()

    def _slice(names: list[str]) -> dict:
        """Keep only the named ratio rows, return {index: {year: value}}.

        financetoolkit >= 2.2.0 returns ratio rows indexed by ratio *name* and
        columns of pandas `Period`. `.to_dict()` therefore yields
        ``{ratio name: {Period: value}}``. json.dumps can serialise *values*
        with ``default=str`` but never *keys* (they must be str/int/float/bool/
        None) — so we must coerce the Period keys to strings *here* before the
        dict ever reaches json.dumps. Callers of the tool get a clean string.
        """
        subset = ratios.loc[ratios.index.intersection(names)]
        return {
            ratio_name: {str(year): value for year, value in row.items()}
            for ratio_name, row in subset.to_dict().items()
        }

    return json.dumps(
        {
            "ticker": ticker.upper(),
            "profitability_ratios": _slice(PROFITABILITY_RATIOS),
            "valuation_ratios": _slice(VALUATION_RATIOS),
            "liquidity_ratios": _slice(LIQUIDITY_RATIOS),
        },
        default=str,
    )
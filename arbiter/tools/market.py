"""
arbiter/tools/market.py
-----------------------
Deterministic market retrieval and calculation tools for Arbiter.
All prices are monthly closes. Calculations are performed using decimal.Decimal.
Market coverage limits are strictly checked.
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Any

from arbiter.data_store import DataStore


# ---------------------------------------------------------------------------
# Market Tool Exceptions
# ---------------------------------------------------------------------------

class MarketToolError(ValueError):
    """Base exception for all market tool errors."""


class MarketCoverageError(MarketToolError):
    """Raised when a symbol is requested that is not in covered_symbols."""

    def __init__(self, symbol: str) -> None:
        super().__init__(f"Instrument '{symbol}' is not covered by the supplied market dataset.")
        self.symbol = symbol


class NoPriceDataError(MarketToolError):
    """Raised when no close price observation is available on or before the date."""

    def __init__(self, symbol: str, date: str) -> None:
        super().__init__(f"No price data available for '{symbol}' on or before {date}.")
        self.symbol = symbol
        self.date = date


# ---------------------------------------------------------------------------
# Private Helpers
# ---------------------------------------------------------------------------

def _parse_date(value: Any, *, context: str = "") -> datetime.date:
    """Parse an ISO date string to datetime.date."""
    if isinstance(value, datetime.date):
        return value
    if not isinstance(value, str) or not value.strip():
        raise MarketToolError(f"Invalid date value {value!r} for {context}.")
    try:
        return datetime.date.fromisoformat(value.strip())
    except ValueError:
        raise MarketToolError(f"Invalid date value {value!r} for {context}.")


# ---------------------------------------------------------------------------
# Public Market Tools
# ---------------------------------------------------------------------------

def get_instrument_details(store: DataStore, symbol: str) -> dict:
    """Retrieve metadata details for the covered *symbol*.

    Returns
    -------
    dict with keys:
        symbol, sector, industry, currency, listed_on, citations
    """
    if symbol not in store.covered_symbols:
        raise MarketCoverageError(symbol)

    inst = store.instrument(symbol)
    if not inst:
        raise MarketCoverageError(symbol)

    return {
        "symbol": symbol,
        "sector": inst.get("sector"),
        "industry": inst.get("industry"),
        "currency": inst.get("currency"),
        "listed_on": inst.get("listed_on"),
        "citations": [symbol]
    }


def get_market_price(store: DataStore, symbol: str, date_str: str) -> dict:
    """Retrieve the monthly close price for *symbol* as-of *date_str*.

    Uses the most recent close observation on or before the requested date.

    Returns
    -------
    dict with keys:
        symbol, requested_date, close_date, close_price, citations
    """
    if symbol not in store.covered_symbols:
        raise MarketCoverageError(symbol)

    target_dt = _parse_date(date_str, context="requested price date")
    prices_list = store.prices(symbol)

    best_entry = None
    best_dt = None

    for p in prices_list:
        p_dt = _parse_date(p["date"], context="price entry date")
        if p_dt <= target_dt:
            if best_dt is None or p_dt > best_dt:
                best_dt = p_dt
                best_entry = p

    if best_entry is None:
        raise NoPriceDataError(symbol, date_str)

    return {
        "symbol": symbol,
        "requested_date": date_str,
        "close_date": best_entry["date"],
        "close_price": best_entry["close"],
        "citations": [symbol]
    }


def get_market_return(store: DataStore, symbol: str, start_date: str, end_date: str) -> dict:
    """Calculate the percentage return of *symbol* between *start_date* and *end_date*."""
    start_info = get_market_price(store, symbol, start_date)
    end_info = get_market_price(store, symbol, end_date)

    p_start = Decimal(start_info["close_price"])
    p_end = Decimal(end_info["close_price"])

    if p_start == Decimal("0"):
        raise MarketToolError("Initial price cannot be zero for return calculation.")

    pct_return = (p_end - p_start) / p_start * Decimal("100")
    pct_return_str = f"{pct_return:.2f}"

    return {
        "symbol": symbol,
        "start_date": start_date,
        "start_price": start_info["close_price"],
        "start_price_date": start_info["close_date"],
        "end_date": end_date,
        "end_price": end_info["close_price"],
        "end_price_date": end_info["close_date"],
        "percentage_return": pct_return_str,
        "citations": [symbol]
    }


def get_symbol_news(store: DataStore, symbol: str) -> list[dict]:
    """Retrieve all news articles on file for the covered *symbol*.

    Returns
    -------
    list of dict with keys:
        id, date, symbol, headline, body, source, citations
    """
    if symbol not in store.covered_symbols:
        raise MarketCoverageError(symbol)

    news_list = store.news_for(symbol)
    result = []
    for n in news_list:
        nid = n.get("id")
        result.append({
            "id": nid,
            "date": n.get("date"),
            "symbol": symbol,
            "headline": n.get("headline"),
            "body": n.get("body"),
            "source": n.get("source"),
            "citations": [nid] if nid else [symbol]
        })
    return result

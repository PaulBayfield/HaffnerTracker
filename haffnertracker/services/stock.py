import asyncio
import logging

from datetime import timedelta

import yfinance as yf

from aiohttp import ClientSession

from ..utils.constants import CHART_RANGES, TICKER
from . import boursorama
from .quote import Quote

logger = logging.getLogger(__name__)


def _fetch_quote() -> Quote:
    ticker = yf.Ticker(TICKER)
    info = ticker.fast_info

    return Quote(
        price=float(info["last_price"]),
        previous_close=float(info["previous_close"]),
        currency=str(info.get("currency", "EUR")),
    )


def _fetch_history(period: str, interval: str = "1d"):
    ticker = yf.Ticker(TICKER)
    return ticker.history(period=period, interval=interval)


async def get_quote(session: ClientSession) -> Quote:
    """Return the real-time Boursorama quote, falling back to (delayed) Yahoo Finance if the scrape fails."""
    try:
        quote = await boursorama.fetch_quote(session)
    except Exception:
        logger.warning("Boursorama quote fetch failed; falling back to yfinance", exc_info=True)
        quote = None

    if quote is not None:
        return quote

    return await asyncio.to_thread(_fetch_quote)


async def get_history(period: str, interval: str = "1d"):
    """Return a pandas DataFrame of OHLCV data for the given yfinance period/interval strings."""
    return await asyncio.to_thread(_fetch_history, period, interval)


async def get_chart_history(range_key: str):
    """Return a pandas DataFrame of OHLCV data for a /chart range key (e.g. "6h", "1d", "1mo").

    Short intraday ranges are fetched with a wider yfinance period (since exchanges are closed
    most of the day) and then trimmed to the requested trailing window relative to the most
    recent bar, so "6h" means the last 6 hours of trading, not the last 6 calendar hours.
    """
    yf_period, yf_interval, window_hours = CHART_RANGES[range_key]
    hist = await get_history(yf_period, yf_interval)

    if window_hours is not None and not hist.empty:
        cutoff = hist.index.max() - timedelta(hours=window_hours)
        hist = hist[hist.index >= cutoff]

    return hist

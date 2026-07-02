import asyncio

from dataclasses import dataclass

import yfinance as yf

from ..utils.constants import TICKER


@dataclass
class Quote:
    price: float
    previous_close: float
    currency: str

    @property
    def change(self) -> float:
        return self.price - self.previous_close

    @property
    def change_pct(self) -> float:
        if self.previous_close == 0:
            return 0.0
        return (self.change / self.previous_close) * 100


def _fetch_quote() -> Quote:
    ticker = yf.Ticker(TICKER)
    info = ticker.fast_info

    return Quote(
        price=float(info["last_price"]),
        previous_close=float(info["previous_close"]),
        currency=str(info.get("currency", "EUR")),
    )


def _fetch_history(period: str):
    ticker = yf.Ticker(TICKER)
    return ticker.history(period=period, interval="1d")


async def get_quote() -> Quote:
    return await asyncio.to_thread(_fetch_quote)


async def get_history(period: str):
    """Return a pandas DataFrame of OHLCV data for the given yfinance period string."""
    return await asyncio.to_thread(_fetch_history, period)

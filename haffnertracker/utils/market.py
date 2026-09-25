from datetime import datetime, timedelta

import pytz

from .constants import (
    MARKET_CLOSE_GRACE_MINUTES,
    MARKET_CLOSE_HOUR,
    MARKET_CLOSE_MINUTE,
    MARKET_OPEN_HOUR,
    MARKET_TIMEZONE,
)


def market_now() -> datetime:
    return datetime.now(pytz.timezone(MARKET_TIMEZONE))


def market_close_time(now: datetime) -> datetime:
    return now.replace(hour=MARKET_CLOSE_HOUR, minute=MARKET_CLOSE_MINUTE, second=0, microsecond=0)


def is_market_hours(now: datetime) -> bool:
    """Weekday trading hours, extended a little past the close so the closing auction is captured."""
    market_open = now.replace(hour=MARKET_OPEN_HOUR, minute=0, second=0, microsecond=0)
    grace_close = market_close_time(now) + timedelta(minutes=MARKET_CLOSE_GRACE_MINUTES)
    return now.weekday() < 5 and market_open <= now <= grace_close

from typing import TYPE_CHECKING, Any

from dPyStatus import StatusServer

from ..services.quote import Quote
from .constants import BOURSORAMA_QUOTE_URL, COMPANY_NAME, TICKER
from .market import is_market_hours, market_now

if TYPE_CHECKING:
    from ..bot import Bot

LATEST_LIMIT = 5


def _quote_payload(quote: Quote) -> dict[str, Any]:
    return {
        "price": quote.price,
        "previous_close": quote.previous_close,
        "change": round(quote.change, 4),
        "change_pct": round(quote.change_pct, 2),
        "open": quote.open,
        "high": quote.high,
        "low": quote.low,
        "volume": quote.volume,
        "currency": quote.currency,
        "source": quote.source,
        "traded_at": quote.traded_at.isoformat() if quote.traded_at else None,
    }


def _loop_payload(loop) -> dict[str, Any]:
    next_iteration = loop.next_iteration
    return {
        "running": loop.is_running(),
        "failed": loop.failed(),
        "next_iteration": next_iteration.isoformat() if next_iteration else None,
    }


def register_extras(bot: "Bot", server: StatusServer) -> None:
    """Expose Haffner-specific state under the status endpoint's `extra` key.

    Everything here reads from memory or the local database, never from the network, so polling the status
    endpoint stays cheap and never adds load on Boursorama or Yahoo.
    """

    @server.extra
    def company() -> dict[str, Any]:
        return {"name": COMPANY_NAME, "ticker": TICKER, "url": BOURSORAMA_QUOTE_URL}

    @server.extra
    async def stock() -> dict[str, Any]:
        tasks_cog = bot.get_cog("Tasks")
        quote = getattr(tasks_cog, "last_quote", None)
        payload: dict[str, Any] = {"market_open": is_market_hours(market_now()), "live": None, "latest_day": None}

        if quote is not None:
            payload["live"] = _quote_payload(quote)

        latest = await bot.entities.prices.get_latest()
        if latest is not None:
            payload["latest_day"] = {
                "date": latest["date"],
                "open": latest["open"],
                "high": latest["high"],
                "low": latest["low"],
                "close": latest["close"],
                "volume": latest["volume"],
            }

        return payload

    @server.extra
    async def forum() -> dict[str, Any]:
        rows = await bot.entities.forum.list_page(0, LATEST_LIMIT)
        return {
            "total": await bot.entities.forum.count(),
            "latest": [
                {
                    "id": row["id"],
                    "author": row["author"],
                    "text": row["text"],
                    "thread": row["thread_title"],
                    "url": row["url"],
                    "posted_at": row["posted_at"],
                }
                for row in rows
            ],
        }

    @server.extra
    async def news() -> dict[str, Any]:
        rows = await bot.entities.news.list_page(0, LATEST_LIMIT)
        return {
            "total": await bot.entities.news.count(),
            "latest": [
                {
                    "title": row["title"],
                    "source": row["source"],
                    "url": row["url"],
                    "published_at": row["published_at"],
                    "posted_at": row["posted_at"],
                }
                for row in rows
            ],
        }

    @server.extra
    async def alerts() -> dict[str, Any]:
        return {"active": len(await bot.entities.alerts.list_active())}

    @server.extra
    async def guilds() -> dict[str, Any]:
        configs = await bot.entities.guild_config.get_all()
        return {
            "configured": len(configs),
            "news_channels": sum(1 for c in configs if c["news_channel_id"]),
            "price_channels": sum(1 for c in configs if c["price_channel_id"]),
            "forum_channels": sum(1 for c in configs if c["forum_channel_id"]),
        }

    @server.extra
    def tasks() -> dict[str, Any] | None:
        tasks_cog = bot.get_cog("Tasks")
        if tasks_cog is None:
            return None
        return {
            "price": _loop_payload(tasks_cog.price_loop),
            "forum": _loop_payload(tasks_cog.forum_loop),
            "news": _loop_payload(tasks_cog.news_loop),
        }

    @server.extra
    async def database() -> bool:
        cursor = await bot.db.execute("SELECT 1")
        return (await cursor.fetchone()) is not None

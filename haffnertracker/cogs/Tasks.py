import logging

from datetime import datetime, timedelta

import discord
import pytz

from discord.ext import commands, tasks

from ..services import news as news_service
from ..services import stock as stock_service
from ..utils.constants import (
    MARKET_CLOSE_HOUR,
    MARKET_CLOSE_MINUTE,
    MARKET_OPEN_HOUR,
    MARKET_TIMEZONE,
)
from ..views.news import PAGE_SIZE, NewsView

logger = logging.getLogger(__name__)


class Tasks(commands.Cog):
    def __init__(self, client: commands.Bot) -> None:
        self.client = client
        self.news_loop.start()
        self.price_loop.start()

    def cog_unload(self) -> None:
        self.news_loop.cancel()
        self.price_loop.cancel()

    @tasks.loop(minutes=30)
    async def news_loop(self) -> None:
        try:
            await self._run_news_loop()
        except Exception:
            logger.exception("news_loop iteration failed; will retry next interval")

    async def _run_news_loop(self) -> None:
        articles = await news_service.fetch_all(self.client.session, self.client.newsapi_key)

        new_articles = []
        for article in articles:
            if await self.client.entities.news.is_seen(article.id):
                continue
            await self.client.entities.news.mark_seen(
                article.id,
                article.title,
                article.source,
                article.url,
                article.published_at,
                article.description,
                article.image_url,
            )
            new_articles.append(article)

        if not new_articles:
            return

        configs = await self.client.entities.guild_config.get_all()
        for config in configs:
            channel_id = config["news_channel_id"]
            if not channel_id:
                continue

            channel = self.client.get_channel(channel_id)
            if channel is None:
                continue

            ordered = list(reversed(new_articles))
            for i in range(0, len(ordered), PAGE_SIZE):
                chunk = ordered[i : i + PAGE_SIZE]
                await channel.send(view=NewsView(chunk))

    @news_loop.before_loop
    async def before_news_loop(self) -> None:
        await self.client.wait_until_ready()

    @tasks.loop(minutes=15)
    async def price_loop(self) -> None:
        try:
            await self._run_price_loop()
        except Exception:
            logger.exception("price_loop iteration failed; will retry next interval")

    async def _run_price_loop(self) -> None:
        tz = pytz.timezone(MARKET_TIMEZONE)
        now = datetime.now(tz)

        if now.weekday() >= 5:
            return

        market_open = now.replace(hour=MARKET_OPEN_HOUR, minute=0, second=0, microsecond=0)
        market_close = now.replace(hour=MARKET_CLOSE_HOUR, minute=MARKET_CLOSE_MINUTE, second=0, microsecond=0)
        if not (market_open <= now <= market_close):
            return

        quote = await stock_service.get_quote()
        await self.check_alerts(quote)

        if now >= market_close - timedelta(minutes=15):
            await self.persist_today()

    @price_loop.before_loop
    async def before_price_loop(self) -> None:
        await self.client.wait_until_ready()

        if await self.client.entities.prices.count() == 0:
            hist = await stock_service.get_history("5y")
            rows = [
                (
                    idx.strftime("%Y-%m-%d"),
                    float(row["Open"]),
                    float(row["High"]),
                    float(row["Low"]),
                    float(row["Close"]),
                    int(row["Volume"]),
                )
                for idx, row in hist.iterrows()
            ]
            if rows:
                await self.client.entities.prices.bulk_upsert(rows)

    async def persist_today(self) -> None:
        hist = await stock_service.get_history("1d")
        if hist.empty:
            return

        idx = hist.index[-1]
        row = hist.iloc[-1]
        await self.client.entities.prices.upsert_day(
            idx.strftime("%Y-%m-%d"),
            float(row["Open"]),
            float(row["High"]),
            float(row["Low"]),
            float(row["Close"]),
            int(row["Volume"]),
        )

    async def check_alerts(self, quote: stock_service.Quote) -> None:
        alerts = await self.client.entities.alerts.list_active()

        for alert in alerts:
            triggered = False
            if alert["kind"] == "price_above" and quote.price >= alert["threshold"]:
                triggered = True
            elif alert["kind"] == "price_below" and quote.price <= alert["threshold"]:
                triggered = True
            elif alert["kind"] == "pct_change" and abs(quote.change_pct) >= alert["threshold"]:
                triggered = True

            if not triggered:
                continue

            await self.client.entities.alerts.deactivate(alert["id"], alert["user_id"])

            try:
                user = self.client.get_user(alert["user_id"]) or await self.client.fetch_user(alert["user_id"])
                await user.send(
                    f"🔔 Haffner Energy alert `#{alert['id']}` triggered: "
                    f"price is {quote.price:.3f} {quote.currency} ({quote.change_pct:+.2f}% today)."
                )
            except discord.HTTPException:
                pass


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Tasks(client))

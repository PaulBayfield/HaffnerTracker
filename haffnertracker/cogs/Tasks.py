import logging

from datetime import datetime, timedelta

import discord
import pytz

from discord.ext import commands, tasks

from ..services import boursorama as forum_service
from ..services import news as news_service
from ..services import stock as stock_service
from ..services.quote import Quote
from ..utils.constants import (
    MARKET_CLOSE_GRACE_MINUTES,
    MARKET_CLOSE_HOUR,
    MARKET_CLOSE_MINUTE,
    MARKET_OPEN_HOUR,
    MARKET_TIMEZONE,
)
from ..views.forum import PAGE_SIZE as FORUM_PAGE_SIZE
from ..views.forum import ForumView
from ..views.news import PAGE_SIZE, NewsView
from ..views.price import PriceView

logger = logging.getLogger(__name__)


class Tasks(commands.Cog):
    def __init__(self, client: commands.Bot) -> None:
        self.client = client
        self._persisted_on: str | None = None
        self.news_loop.start()
        self.price_loop.start()
        self.forum_loop.start()

    def cog_unload(self) -> None:
        self.news_loop.cancel()
        self.price_loop.cancel()
        self.forum_loop.cancel()

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
    async def forum_loop(self) -> None:
        try:
            await self._run_forum_loop()
        except Exception:
            logger.exception("forum_loop iteration failed; will retry next interval")

    async def _run_forum_loop(self) -> None:
        comments = await forum_service.fetch_all_comments(self.client.session)

        new_comments = []
        for comment in comments:
            if await self.client.entities.forum.is_seen(comment.id):
                continue
            await self.client.entities.forum.mark_seen(
                comment.id, comment.thread_id, comment.thread_title, comment.author, comment.text, comment.url
            )
            new_comments.append(comment)

        if not new_comments:
            return

        configs = await self.client.entities.guild_config.get_all()
        for config in configs:
            channel_id = config["forum_channel_id"]
            if not channel_id:
                continue

            channel = self.client.get_channel(channel_id)
            if channel is None:
                continue

            ordered = list(reversed(new_comments))
            for i in range(0, len(ordered), FORUM_PAGE_SIZE):
                chunk = ordered[i : i + FORUM_PAGE_SIZE]
                await channel.send(view=ForumView(chunk))

    @forum_loop.before_loop
    async def before_forum_loop(self) -> None:
        await self.client.wait_until_ready()

        if await self.client.entities.forum.count() == 0:
            comments = await forum_service.fetch_all_comments(self.client.session)
            for comment in comments:
                await self.client.entities.forum.mark_seen(
                    comment.id, comment.thread_id, comment.thread_title, comment.author, comment.text, comment.url
                )

    @tasks.loop(minutes=1)
    async def price_loop(self) -> None:
        try:
            await self._run_price_loop()
        except Exception:
            logger.exception("price_loop iteration failed; will retry next interval")

    async def _run_price_loop(self) -> None:
        tz = pytz.timezone(MARKET_TIMEZONE)
        now = datetime.now(tz)

        market_open = now.replace(hour=MARKET_OPEN_HOUR, minute=0, second=0, microsecond=0)
        market_close = now.replace(hour=MARKET_CLOSE_HOUR, minute=MARKET_CLOSE_MINUTE, second=0, microsecond=0)
        market_hours = now.weekday() < 5 and market_open <= now <= market_close + timedelta(
            minutes=MARKET_CLOSE_GRACE_MINUTES
        )

        if not market_hours:
            # Outside market hours the live message is left as-is; only create it for guilds that don't have one yet.
            if await self._guilds_missing_price_message():
                quote = await stock_service.get_quote(self.client.session)
                await self.update_price_messages(quote, only_missing=True)
            return

        quote = await stock_service.get_quote(self.client.session)
        await self.check_alerts(quote)
        await self.update_price_messages(quote)
        await self.persist_quote(quote, now, market_close)

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

    async def persist_quote(self, quote: Quote, now: datetime, market_close: datetime) -> None:
        today = now.strftime("%Y-%m-%d")

        # Boursorama gives the full day's OHLCV, so today's row can be kept current on every tick. Its trade date
        # guards against writing a stale session under today's date (e.g. on a market holiday).
        if (
            quote.traded_at is not None
            and quote.traded_at.strftime("%Y-%m-%d") == today
            and None not in (quote.open, quote.high, quote.low, quote.volume)
        ):
            await self.client.entities.prices.upsert_day(
                today, quote.open, quote.high, quote.low, quote.price, quote.volume
            )
            return

        if now >= market_close - timedelta(minutes=15) and self._persisted_on != today:
            await self.persist_today()
            self._persisted_on = today

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

    async def _guilds_missing_price_message(self) -> bool:
        configs = await self.client.entities.guild_config.get_all()
        return any(
            config["price_channel_id"]
            and not config["price_message_id"]
            and self.client.get_channel(config["price_channel_id"]) is not None
            for config in configs
        )

    async def update_price_messages(self, quote: Quote, only_missing: bool = False) -> None:
        """Keep a single live price message per guild, editing it in place rather than posting a new one."""
        configs = await self.client.entities.guild_config.get_all()

        for config in configs:
            channel_id = config["price_channel_id"]
            if not channel_id:
                continue

            message_id = config["price_message_id"]
            if only_missing and message_id:
                continue

            channel = self.client.get_channel(channel_id)
            if channel is None:
                continue

            view = PriceView(self.client, quote)

            if message_id:
                try:
                    await channel.get_partial_message(message_id).edit(view=view)
                    continue
                except discord.NotFound:
                    pass  # message was deleted; post a fresh one below
                except discord.HTTPException:
                    logger.warning("Failed to edit price message in guild %s", config["guild_id"], exc_info=True)
                    continue

            try:
                message = await channel.send(view=view)
            except discord.HTTPException:
                logger.warning("Failed to post price message in guild %s", config["guild_id"], exc_info=True)
                continue

            await self.client.entities.guild_config.set_price_message(config["guild_id"], message.id)

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

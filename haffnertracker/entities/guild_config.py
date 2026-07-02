import aiosqlite


class GuildConfig:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db

    async def get(self, guild_id: int) -> aiosqlite.Row | None:
        cursor = await self.db.execute("SELECT * FROM guild_config WHERE guild_id = ?", (guild_id,))
        return await cursor.fetchone()

    async def get_all(self) -> list[aiosqlite.Row]:
        cursor = await self.db.execute("SELECT * FROM guild_config")
        return await cursor.fetchall()

    async def set_news_channel(self, guild_id: int, channel_id: int) -> None:
        await self.db.execute(
            """
            INSERT INTO guild_config (guild_id, news_channel_id) VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET news_channel_id = excluded.news_channel_id
            """,
            (guild_id, channel_id),
        )
        await self.db.commit()

    async def set_price_channel(self, guild_id: int, channel_id: int) -> None:
        await self.db.execute(
            """
            INSERT INTO guild_config (guild_id, price_channel_id) VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET price_channel_id = excluded.price_channel_id
            """,
            (guild_id, channel_id),
        )
        await self.db.commit()

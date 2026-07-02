from datetime import datetime

import aiosqlite


class Prices:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db

    async def upsert_day(self, date: str, open_: float, high: float, low: float, close: float, volume: int) -> None:
        await self.db.execute(
            """
            INSERT INTO price_history (date, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                open=excluded.open, high=excluded.high, low=excluded.low,
                close=excluded.close, volume=excluded.volume
            """,
            (date, open_, high, low, close, volume),
        )
        await self.db.commit()

    async def bulk_upsert(self, rows: list[tuple]) -> None:
        await self.db.executemany(
            """
            INSERT INTO price_history (date, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                open=excluded.open, high=excluded.high, low=excluded.low,
                close=excluded.close, volume=excluded.volume
            """,
            rows,
        )
        await self.db.commit()

    async def get_history(self, since: datetime | None = None) -> list[aiosqlite.Row]:
        if since is not None:
            cursor = await self.db.execute(
                "SELECT * FROM price_history WHERE date >= ? ORDER BY date ASC",
                (since.strftime("%Y-%m-%d"),),
            )
        else:
            cursor = await self.db.execute("SELECT * FROM price_history ORDER BY date ASC")

        return await cursor.fetchall()

    async def get_latest(self) -> aiosqlite.Row | None:
        cursor = await self.db.execute("SELECT * FROM price_history ORDER BY date DESC LIMIT 1")
        return await cursor.fetchone()

    async def count(self) -> int:
        cursor = await self.db.execute("SELECT COUNT(*) as c FROM price_history")
        row = await cursor.fetchone()
        return row["c"]

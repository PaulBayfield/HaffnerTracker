from datetime import datetime, timezone

import aiosqlite


class News:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db

    async def is_seen(self, article_id: str) -> bool:
        cursor = await self.db.execute("SELECT 1 FROM seen_news WHERE id = ?", (article_id,))
        return await cursor.fetchone() is not None

    async def mark_seen(self, article_id: str, title: str, source: str, url: str, published_at: str | None) -> None:
        await self.db.execute(
            """
            INSERT OR IGNORE INTO seen_news (id, title, source, url, published_at, posted_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (article_id, title, source, url, published_at, datetime.now(timezone.utc).isoformat()),
        )
        await self.db.commit()

    async def list_page(self, offset: int, limit: int) -> list[aiosqlite.Row]:
        cursor = await self.db.execute(
            "SELECT * FROM seen_news ORDER BY posted_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        return await cursor.fetchall()

    async def count(self) -> int:
        cursor = await self.db.execute("SELECT COUNT(*) as c FROM seen_news")
        row = await cursor.fetchone()
        return row["c"]

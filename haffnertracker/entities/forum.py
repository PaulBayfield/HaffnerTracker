from datetime import datetime, timezone

import aiosqlite


class Forum:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db

    async def is_seen(self, comment_id: str) -> bool:
        cursor = await self.db.execute("SELECT 1 FROM seen_forum_comments WHERE id = ?", (comment_id,))
        return await cursor.fetchone() is not None

    async def mark_seen(
        self,
        comment_id: str,
        thread_id: str,
        thread_title: str,
        author: str,
        text: str,
        url: str,
    ) -> None:
        await self.db.execute(
            """
            INSERT OR IGNORE INTO seen_forum_comments (id, thread_id, thread_title, author, text, url, posted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                comment_id,
                thread_id,
                thread_title,
                author,
                text,
                url,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        await self.db.commit()

    async def list_page(self, offset: int, limit: int) -> list[aiosqlite.Row]:
        cursor = await self.db.execute(
            "SELECT * FROM seen_forum_comments ORDER BY posted_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        return await cursor.fetchall()

    async def count(self) -> int:
        cursor = await self.db.execute("SELECT COUNT(*) as c FROM seen_forum_comments")
        row = await cursor.fetchone()
        return row["c"]

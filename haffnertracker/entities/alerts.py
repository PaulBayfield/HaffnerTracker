from datetime import datetime, timezone

import aiosqlite


class Alerts:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db

    async def create(self, user_id: int, guild_id: int, kind: str, threshold: float) -> int:
        cursor = await self.db.execute(
            """
            INSERT INTO alerts (user_id, guild_id, kind, threshold, created_at, active)
            VALUES (?, ?, ?, ?, ?, 1)
            """,
            (user_id, guild_id, kind, threshold, datetime.now(timezone.utc).isoformat()),
        )
        await self.db.commit()
        return cursor.lastrowid

    async def list_for_user(self, user_id: int) -> list[aiosqlite.Row]:
        cursor = await self.db.execute(
            "SELECT * FROM alerts WHERE user_id = ? AND active = 1 ORDER BY id ASC",
            (user_id,),
        )
        return await cursor.fetchall()

    async def list_active(self) -> list[aiosqlite.Row]:
        cursor = await self.db.execute("SELECT * FROM alerts WHERE active = 1")
        return await cursor.fetchall()

    async def deactivate(self, alert_id: int, user_id: int) -> bool:
        cursor = await self.db.execute(
            "UPDATE alerts SET active = 0 WHERE id = ? AND user_id = ?",
            (alert_id, user_id),
        )
        await self.db.commit()
        return cursor.rowcount > 0

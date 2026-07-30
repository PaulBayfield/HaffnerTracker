import aiosqlite
import pytest

from haffnertracker.utils.db import _migrate


@pytest.fixture
async def legacy_db():
    """A seen_news table as it looked before description/image_url were added."""
    db = await aiosqlite.connect(":memory:")
    db.row_factory = aiosqlite.Row
    await db.execute(
        """
        CREATE TABLE seen_news (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            source TEXT NOT NULL,
            url TEXT NOT NULL,
            published_at TEXT,
            posted_at TEXT NOT NULL
        )
        """
    )
    await db.execute(
        "INSERT INTO seen_news (id, title, source, url, published_at, posted_at) VALUES (?, ?, ?, ?, ?, ?)",
        ("1", "Title", "Source", "https://example.com", "2026-07-10", "2026-07-10T00:00:00Z"),
    )
    await db.commit()
    try:
        yield db
    finally:
        await db.close()


@pytest.fixture
async def legacy_guild_config_db():
    """A guild_config table as it looked before forum_channel_id was added."""
    db = await aiosqlite.connect(":memory:")
    db.row_factory = aiosqlite.Row
    await db.execute(
        """
        CREATE TABLE guild_config (
            guild_id INTEGER PRIMARY KEY,
            news_channel_id INTEGER,
            price_channel_id INTEGER
        )
        """
    )
    await db.execute("INSERT INTO guild_config (guild_id, news_channel_id) VALUES (?, ?)", (1, 123))
    await db.commit()
    try:
        yield db
    finally:
        await db.close()


class TestMigrate:
    async def test_adds_missing_columns_without_losing_existing_rows(self, legacy_db):
        await _migrate(legacy_db)
        await legacy_db.commit()

        cursor = await legacy_db.execute("PRAGMA table_info(seen_news)")
        columns = {row["name"] for row in await cursor.fetchall()}
        assert {"description", "image_url"}.issubset(columns)

        cursor = await legacy_db.execute("SELECT * FROM seen_news WHERE id = ?", ("1",))
        row = await cursor.fetchone()
        assert row["title"] == "Title"
        assert row["description"] is None
        assert row["image_url"] is None

    async def test_is_a_no_op_on_a_table_that_already_has_the_columns(self, legacy_db):
        await _migrate(legacy_db)
        await _migrate(legacy_db)  # should not raise on the second pass
        await legacy_db.commit()

        cursor = await legacy_db.execute("PRAGMA table_info(seen_news)")
        columns = [row["name"] for row in await cursor.fetchall()]
        assert columns.count("description") == 1

    async def test_adds_forum_channel_id_without_losing_existing_rows(self, legacy_guild_config_db):
        await _migrate(legacy_guild_config_db)
        await legacy_guild_config_db.commit()

        cursor = await legacy_guild_config_db.execute("PRAGMA table_info(guild_config)")
        columns = {row["name"] for row in await cursor.fetchall()}
        assert "forum_channel_id" in columns

        cursor = await legacy_guild_config_db.execute("SELECT * FROM guild_config WHERE guild_id = ?", (1,))
        row = await cursor.fetchone()
        assert row["news_channel_id"] == 123
        assert row["forum_channel_id"] is None

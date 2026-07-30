import aiosqlite
import pytest

from haffnertracker.entities.forum import Forum
from haffnertracker.utils.db import SCHEMA


@pytest.fixture
async def forum_entity():
    db = await aiosqlite.connect(":memory:")
    db.row_factory = aiosqlite.Row
    await db.executescript(SCHEMA)
    await db.commit()
    try:
        yield Forum(db)
    finally:
        await db.close()


class TestForum:
    async def test_unseen_comment_is_not_seen(self, forum_entity):
        assert await forum_entity.is_seen("111111") is False

    async def test_mark_seen_then_is_seen(self, forum_entity):
        await forum_entity.mark_seen("111111", "1", "Sujet", "author", "text", "https://example.com#111111")
        assert await forum_entity.is_seen("111111") is True

    async def test_mark_seen_is_idempotent(self, forum_entity):
        await forum_entity.mark_seen("111111", "1", "Sujet", "author", "text", "https://example.com#111111")
        await forum_entity.mark_seen("111111", "1", "Sujet", "different", "different", "https://example.com#111111")

        assert await forum_entity.count() == 1

    async def test_list_page_orders_most_recently_posted_first(self, forum_entity):
        await forum_entity.mark_seen("first", "1", "Sujet", "author", "text", "https://example.com#first")
        await forum_entity.mark_seen("second", "1", "Sujet", "author", "text", "https://example.com#second")

        rows = await forum_entity.list_page(0, 10)
        assert [row["id"] for row in rows] == ["second", "first"]

    async def test_count_reflects_number_of_seen_comments(self, forum_entity):
        assert await forum_entity.count() == 0

        await forum_entity.mark_seen("first", "1", "Sujet", "author", "text", "https://example.com#first")
        await forum_entity.mark_seen("second", "1", "Sujet", "author", "text", "https://example.com#second")

        assert await forum_entity.count() == 2

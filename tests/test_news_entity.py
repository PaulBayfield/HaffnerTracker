import aiosqlite
import pytest

from haffnertracker.entities.news import News
from haffnertracker.utils.db import SCHEMA


@pytest.fixture
async def news_entity():
    db = await aiosqlite.connect(":memory:")
    db.row_factory = aiosqlite.Row
    await db.executescript(SCHEMA)
    await db.commit()
    try:
        yield News(db)
    finally:
        await db.close()


class TestNews:
    async def test_unseen_article_is_not_seen(self, news_entity):
        assert await news_entity.is_seen("abc123") is False

    async def test_mark_seen_then_is_seen(self, news_entity):
        await news_entity.mark_seen("abc123", "Title", "Source", "https://example.com", "2026-07-10T08:00:00Z")
        assert await news_entity.is_seen("abc123") is True

    async def test_mark_seen_is_idempotent(self, news_entity):
        await news_entity.mark_seen("abc123", "Title", "Source", "https://example.com", None)
        await news_entity.mark_seen("abc123", "Different title", "Different source", "https://example.com", None)

        assert await news_entity.count() == 1

    async def test_mark_seen_persists_description_and_image(self, news_entity):
        await news_entity.mark_seen(
            "abc123",
            "Title",
            "Source",
            "https://example.com",
            "2026-07-10T08:00:00Z",
            description="A short summary",
            image_url="https://example.com/image.jpg",
        )

        rows = await news_entity.list_page(0, 10)
        assert rows[0]["description"] == "A short summary"
        assert rows[0]["image_url"] == "https://example.com/image.jpg"

    async def test_list_page_orders_most_recently_posted_first(self, news_entity):
        await news_entity.mark_seen("first", "First", "Source", "https://example.com/1", None)
        await news_entity.mark_seen("second", "Second", "Source", "https://example.com/2", None)

        rows = await news_entity.list_page(0, 10)
        assert [row["id"] for row in rows] == ["second", "first"]

    async def test_count_reflects_number_of_seen_articles(self, news_entity):
        assert await news_entity.count() == 0

        await news_entity.mark_seen("first", "First", "Source", "https://example.com/1", None)
        await news_entity.mark_seen("second", "Second", "Source", "https://example.com/2", None)

        assert await news_entity.count() == 2

from types import SimpleNamespace

import pytest

from haffnertracker.entities.entities import Entities
from haffnertracker.services.quote import Quote
from haffnertracker.utils.db import connect
from haffnertracker.utils.status import register_extras


class _FakeServer:
    def __init__(self) -> None:
        self.extras = {}

    def extra(self, func):
        self.extras[func.__name__] = func
        return func


class _FakeLoop:
    next_iteration = None

    def is_running(self) -> bool:
        return True

    def failed(self) -> bool:
        return False


@pytest.fixture
async def bot(tmp_path):
    db = await connect(str(tmp_path / "test.db"))
    tasks_cog = SimpleNamespace(
        last_quote=Quote(0.788, 0.79, "EUR", "Boursorama", 0.76, 0.794, 0.74, 2747660),
        price_loop=_FakeLoop(),
        forum_loop=_FakeLoop(),
        news_loop=_FakeLoop(),
    )
    fake = SimpleNamespace(db=db, entities=Entities(db), get_cog=lambda name: tasks_cog if name == "Tasks" else None)
    try:
        yield fake
    finally:
        await db.close()


async def _call(func):
    result = func()
    return await result if hasattr(result, "__await__") else result


class TestRegisterExtras:
    async def test_exposes_live_quote_and_latest_forum_comments(self, bot):
        await bot.entities.forum.mark_seen("c1", "t1", "Sujet", "ref1929", "Contrat signé", "https://x/#c1")
        server = _FakeServer()

        register_extras(bot, server)

        stock = await _call(server.extras["stock"])
        assert stock["live"]["price"] == 0.788
        assert stock["live"]["change_pct"] == -0.25
        assert stock["latest_day"] is None

        forum = await _call(server.extras["forum"])
        assert forum["total"] == 1
        assert forum["latest"][0]["author"] == "ref1929"

        assert (await _call(server.extras["tasks"]))["price"]["running"] is True
        assert await _call(server.extras["database"]) is True

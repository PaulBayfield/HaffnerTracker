import logging

from os import environ, listdir
from pathlib import Path

import discord

from aiohttp import ClientSession
from discord.ext import commands
from dotenv import load_dotenv

from .entities.entities import Entities
from .utils.db import connect

load_dotenv(dotenv_path=".env")

logger = logging.getLogger(__name__)


class Bot(commands.Bot):
    session: ClientSession

    def __init__(self) -> None:
        intents = discord.Intents(messages=True, guilds=True)
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
            max_messages=None,
            help_command=None,
            owner_ids={int(environ["OWNER_ID"])} if environ.get("OWNER_ID") else None,
            allowed_mentions=discord.AllowedMentions(everyone=False, users=False, roles=False, replied_user=True),
            activity=discord.CustomActivity(name="💰 • Let's make money!"),
            status=discord.Status.online,
        )

        self.env = environ.get("ENV", "dev")
        self.newsapi_key = environ.get("NEWSAPI_KEY", "")
        self.path = str(Path(__file__).parent)
        self.ready = False

    async def setup_hook(self) -> None:
        db = await connect("data/haffnertracker.db")
        self.db = db
        self.entities = Entities(db)

        for file in listdir(self.path + "/cogs"):
            if file.endswith(".py") and not file.startswith("_"):
                try:
                    await self.load_extension(f"haffnertracker.cogs.{file[:-3]}")
                    logger.info("Loaded %s cog", file[:-3])
                except Exception:
                    logger.exception("Error loading %s cog", file[:-3])

    async def on_ready(self) -> None:
        logger.info("Logged in as %s (%s) — HaffnerTracker is now online!", self.user.name, self.user.id)
        self.ready = True

    async def close(self) -> None:
        await self.session.close()
        await self.db.close()
        await super().close()

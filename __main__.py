import asyncio
import logging
import logging.handlers

from os import environ

from aiohttp import ClientSession
from dotenv import load_dotenv

from haffnertracker.bot import Bot

load_dotenv(dotenv_path=".env")


async def main():
    logger = logging.getLogger("discord")
    logger.setLevel(logging.INFO)

    handler = logging.handlers.RotatingFileHandler(
        filename="discord.log",
        encoding="utf-8",
        maxBytes=32 * 1024 * 1024,
        backupCount=5,
    )
    dt_fmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter("[{asctime}] [{levelname:<8}] {name}: {message}", dt_fmt, style="{")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    client = Bot()

    async with ClientSession() as session:
        async with client:
            client.session = session
            await client.start(environ["TOKEN"], reconnect=True)


asyncio.run(main())

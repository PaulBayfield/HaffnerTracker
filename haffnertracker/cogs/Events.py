import logging

import discord

from discord.ext import commands

logger = logging.getLogger(__name__)


class Events(commands.Cog):
    def __init__(self, client: commands.Bot) -> None:
        self.client = client

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild) -> None:
        logger.info("Joined guild: %s (%s)", guild.name, guild.id)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Events(client))

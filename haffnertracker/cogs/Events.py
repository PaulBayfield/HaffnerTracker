import discord

from discord.ext import commands


class Events(commands.Cog):
    def __init__(self, client: commands.Bot) -> None:
        self.client = client

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild) -> None:
        print(f"Joined guild: {guild.name} ({guild.id})")


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Events(client))

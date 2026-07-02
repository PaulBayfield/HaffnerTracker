import discord

from discord import Interaction, app_commands
from discord.ext import commands

from ..views.info import InfoView


class Admin(commands.Cog):
    def __init__(self, client: commands.Bot) -> None:
        self.client = client

    @app_commands.command(name="setnewschannel", description="Set the channel where news updates are posted")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_news_channel(self, interaction: Interaction, channel: discord.TextChannel) -> None:
        await self.client.entities.guild_config.set_news_channel(interaction.guild_id, channel.id)
        await interaction.response.send_message(
            view=InfoView(f"News channel set to {channel.mention}."), ephemeral=True
        )

    @app_commands.command(name="setpricechannel", description="Set the channel where daily price updates are posted")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_price_channel(self, interaction: Interaction, channel: discord.TextChannel) -> None:
        await self.client.entities.guild_config.set_price_channel(interaction.guild_id, channel.id)
        await interaction.response.send_message(
            view=InfoView(f"Price channel set to {channel.mention}."), ephemeral=True
        )

    @commands.command(name="sync")
    @commands.is_owner()
    async def sync(self, ctx: commands.Context) -> None:
        """Sync application (slash) commands with Discord. Mention the bot to run: @HaffnerTracker sync"""
        synced = await self.client.tree.sync()
        await ctx.send(f"Synced {len(synced)} application commands.")


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Admin(client))

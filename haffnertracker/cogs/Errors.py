from discord import Interaction, app_commands
from discord.ext import commands

from ..utils.constants import COLOR_ERROR
from ..views.info import InfoView


class Errors(commands.Cog):
    def __init__(self, client: commands.Bot) -> None:
        self.client = client
        self.client.tree.on_error = self.on_app_command_error

    async def on_app_command_error(self, interaction: Interaction, error: app_commands.AppCommandError) -> None:
        if isinstance(error, app_commands.CommandOnCooldown):
            message = f"This command is on cooldown, try again in {error.retry_after:.0f}s."
        elif isinstance(error, app_commands.MissingPermissions):
            message = "You don't have permission to use this command."
        else:
            message = "Something went wrong while running that command."
            print(f"Unhandled app command error: {error!r}")

        view = InfoView(message, COLOR_ERROR)
        if interaction.response.is_done():
            await interaction.followup.send(view=view, ephemeral=True)
        else:
            await interaction.response.send_message(view=view, ephemeral=True)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Errors(client))

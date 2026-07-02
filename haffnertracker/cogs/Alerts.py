from typing import Literal

from discord import Interaction, app_commands
from discord.ext import commands

from ..utils.constants import COLOR_NEUTRAL
from ..views.info import InfoView

AlertKind = Literal["price_above", "price_below", "pct_change"]

KIND_LABELS = {
    "price_above": "price above",
    "price_below": "price below",
    "pct_change": "daily move of at least",
}


class Alerts(commands.Cog):
    def __init__(self, client: commands.Bot) -> None:
        self.client = client

    alert_group = app_commands.Group(name="alert", description="Manage your personal Haffner Energy price alerts")

    @alert_group.command(name="set", description="Get a DM when the price crosses a threshold")
    async def set_alert(self, interaction: Interaction, kind: AlertKind, threshold: float) -> None:
        alert_id = await self.client.entities.alerts.create(interaction.user.id, interaction.guild_id, kind, threshold)
        content = f"### 🔔 Alert `#{alert_id}` set\nDM me when {KIND_LABELS[kind]} **{threshold}**."
        await interaction.response.send_message(view=InfoView(content, COLOR_NEUTRAL), ephemeral=True)

    @alert_group.command(name="list", description="List your active alerts")
    async def list_alerts(self, interaction: Interaction) -> None:
        alerts = await self.client.entities.alerts.list_for_user(interaction.user.id)
        if not alerts:
            await interaction.response.send_message(view=InfoView("You have no active alerts."), ephemeral=True)
            return

        lines = [f"`#{a['id']}` — {KIND_LABELS[a['kind']]} {a['threshold']}" for a in alerts]
        content = "### Your active alerts\n" + "\n".join(lines)
        await interaction.response.send_message(view=InfoView(content, COLOR_NEUTRAL), ephemeral=True)

    @alert_group.command(name="remove", description="Remove one of your alerts")
    async def remove_alert(self, interaction: Interaction, alert_id: int) -> None:
        ok = await self.client.entities.alerts.deactivate(alert_id, interaction.user.id)
        message = f"Alert `#{alert_id}` removed." if ok else "No active alert with that ID belongs to you."
        await interaction.response.send_message(view=InfoView(message), ephemeral=True)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Alerts(client))

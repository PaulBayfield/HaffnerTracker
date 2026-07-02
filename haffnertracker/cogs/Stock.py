from typing import Literal

import discord

from discord import Interaction, app_commands
from discord.ext import commands

from ..services import stock as stock_service
from ..utils.charts import render_price_chart
from ..utils.constants import CHART_PERIODS
from ..views.chart import ChartView
from ..views.info import InfoView
from ..views.price import PriceView


class Stock(commands.Cog):
    def __init__(self, client: commands.Bot) -> None:
        self.client = client

    @app_commands.command(name="price", description="Get the current Haffner Energy (ALHAF.PA) price")
    async def price(self, interaction: Interaction) -> None:
        await interaction.response.defer()

        quote = await stock_service.get_quote()
        await interaction.followup.send(view=PriceView(self.client, quote))

    @app_commands.command(name="chart", description="Show a Haffner Energy price chart")
    async def chart(
        self,
        interaction: Interaction,
        period: Literal["1w", "1mo", "3mo", "1y", "all"] = "1mo",
    ) -> None:
        await interaction.response.defer()

        hist = await stock_service.get_history(CHART_PERIODS[period])
        if hist.empty:
            await interaction.followup.send(view=InfoView("No price data available for that period."))
            return

        dates = hist.index.to_pydatetime().tolist()
        closes = hist["Close"].tolist()

        buf = render_price_chart(dates, closes)
        file = discord.File(buf, filename="chart.png")
        await interaction.followup.send(view=ChartView(file, period), file=file)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Stock(client))

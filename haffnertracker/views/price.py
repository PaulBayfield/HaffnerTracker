import discord

from ..services.stock import Quote
from ..utils.constants import COLOR_DOWN, COLOR_UP, COMPANY_NAME, TICKER


class PriceView(discord.ui.LayoutView):
    def __init__(self, client: discord.Client, quote: Quote) -> None:
        super().__init__()

        up = quote.change >= 0
        emoji = "🟢" if up else "🔴"

        content = (
            f"### {emoji} {COMPANY_NAME} ({TICKER})\n"
            f"**{quote.price:.3f} {quote.currency}**\n"
            f"-# {quote.change:+.3f} ({quote.change_pct:+.2f}%) today"
        )

        self.add_item(
            discord.ui.Container(
                discord.ui.Section(content, accessory=discord.ui.Thumbnail(media=client.user.display_avatar.url)),
                accent_colour=COLOR_UP if up else COLOR_DOWN,
            )
        )

import discord

from ..services.quote import Quote
from ..utils.constants import COLOR_DOWN, COLOR_UP, COMPANY_NAME, TICKER


def _format_volume(volume: int) -> str:
    return f"{volume:,}".replace(",", " ")


class PriceView(discord.ui.LayoutView):
    def __init__(self, client: discord.Client, quote: Quote) -> None:
        super().__init__()

        up = quote.change >= 0
        emoji = "🟢" if up else "🔴"

        lines = [
            f"### {emoji} {COMPANY_NAME} ({TICKER})",
            f"**{quote.price:.4f} {quote.currency}**",
            f"-# {quote.change:+.4f} ({quote.change_pct:+.2f}%) today",
        ]

        if quote.open is not None and quote.high is not None and quote.low is not None:
            lines.append(f"Open {quote.open:.4f} · High {quote.high:.4f} · Low {quote.low:.4f}")
        if quote.volume is not None:
            lines.append(f"Volume {_format_volume(quote.volume)}")

        footer = f"Source: {quote.source}"
        if quote.traded_at is not None:
            footer += f" · last trade <t:{int(quote.traded_at.timestamp())}:f>"
        lines.append(f"-# {footer}")

        self.add_item(
            discord.ui.Container(
                discord.ui.Section(
                    "\n".join(lines), accessory=discord.ui.Thumbnail(media=client.user.display_avatar.url)
                ),
                accent_colour=COLOR_UP if up else COLOR_DOWN,
            )
        )

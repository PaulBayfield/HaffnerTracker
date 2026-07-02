import discord

from ..utils.constants import COLOR_NEUTRAL, COMPANY_NAME, TICKER


class ChartView(discord.ui.LayoutView):
    def __init__(self, file: discord.File, period_label: str) -> None:
        super().__init__()

        self.add_item(
            discord.ui.Container(
                discord.ui.TextDisplay(f"### {COMPANY_NAME} ({TICKER}) — {period_label}"),
                discord.ui.MediaGallery(discord.MediaGalleryItem(media=file)),
                accent_colour=COLOR_NEUTRAL,
            )
        )

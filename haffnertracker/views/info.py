import discord


class InfoView(discord.ui.LayoutView):
    """A single-container text message, used for confirmations, lists, and errors."""

    def __init__(self, content: str, accent_color: int | None = None) -> None:
        super().__init__()
        self.add_item(discord.ui.Container(discord.ui.TextDisplay(content), accent_colour=accent_color))

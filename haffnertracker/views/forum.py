import math

import discord

from ..entities.entities import Entities
from ..services.boursorama import ForumComment
from ..utils.constants import COLOR_NEUTRAL
from .info import InfoView

PAGE_SIZE = 5


def _comment_text(comment: ForumComment) -> str:
    lines = [f"**{comment.thread_title}**", f"-# {comment.author}", comment.text]
    return "\n".join(lines)


def _comment_sections(comments: list[ForumComment]) -> list[discord.ui.Item]:
    items: list[discord.ui.Item] = []
    for i, comment in enumerate(comments):
        if i > 0:
            items.append(discord.ui.Separator())

        accessory = discord.ui.Button(label="Voir", style=discord.ButtonStyle.link, url=comment.url)
        items.append(discord.ui.Section(_comment_text(comment), accessory=accessory))
    return items


class ForumView(discord.ui.LayoutView):
    """A static digest of Boursorama forum comments, used for /forum latest and the auto-post loop."""

    def __init__(self, comments: list[ForumComment], heading: str = "💬 New Boursorama forum comments") -> None:
        super().__init__()

        children = [discord.ui.TextDisplay(f"### {heading}"), *_comment_sections(comments)]
        self.add_item(discord.ui.Container(*children, accent_colour=COLOR_NEUTRAL))


class ForumAllView(discord.ui.LayoutView):
    """A paginated browser over every previously-seen forum comment, for /forum all."""

    def __init__(self, entities: Entities, page: int, total: int, comments: list[ForumComment], author_id: int) -> None:
        super().__init__(timeout=300)

        self.entities = entities
        self.page = page
        self.total = total
        self.total_pages = max(1, math.ceil(total / PAGE_SIZE))
        self.author_id = author_id
        self.message: discord.Message | None = None

        heading = f"### 🗨️ All Boursorama forum comments — page {self.page + 1}/{self.total_pages}"
        children = [discord.ui.TextDisplay(heading), *_comment_sections(comments)]
        children.append(self._NavigationRow(self))

        self.add_item(discord.ui.Container(*children, accent_colour=COLOR_NEUTRAL))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.author_id:
            return True

        await interaction.response.send_message(
            view=InfoView(
                "Only the person who ran this command can navigate it — run `/forum all` yourself to browse."
            ),
            ephemeral=True,
        )
        return False

    class _NavigationRow(discord.ui.ActionRow):
        def __init__(self, paginator: "ForumAllView") -> None:
            super().__init__()
            self.paginator = paginator
            self.previous_button.disabled = paginator.page <= 0
            self.next_button.disabled = paginator.page >= paginator.total_pages - 1

        @discord.ui.button(label="◀ Previous", style=discord.ButtonStyle.secondary)
        async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
            await self.paginator.go_to_page(interaction, self.paginator.page - 1)

        @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
        async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
            await self.paginator.go_to_page(interaction, self.paginator.page + 1)

    async def go_to_page(self, interaction: discord.Interaction, page: int) -> None:
        page = max(0, min(page, self.total_pages - 1))
        rows = await self.entities.forum.list_page(page * PAGE_SIZE, PAGE_SIZE)
        comments = [ForumComment.from_row(row) for row in rows]

        new_view = ForumAllView(self.entities, page, self.total, comments, self.author_id)
        new_view.message = self.message
        await interaction.response.edit_message(view=new_view)

    async def on_timeout(self) -> None:
        for child in self.walk_children():
            if isinstance(child, discord.ui.Button):
                child.disabled = True

        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass

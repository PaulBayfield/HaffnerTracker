from discord import Interaction, app_commands
from discord.ext import commands

from ..services import boursorama as forum_service
from ..views.forum import PAGE_SIZE, ForumAllView, ForumView
from ..views.info import InfoView


class Forum(commands.Cog):
    def __init__(self, client: commands.Bot) -> None:
        self.client = client

    forum_group = app_commands.Group(name="forum", description="Boursorama forum comments")

    @forum_group.command(name="latest", description="Fetch and post the latest Boursorama forum comments now")
    @app_commands.checks.cooldown(1, 300, key=lambda i: i.guild_id)
    async def latest(self, interaction: Interaction) -> None:
        await interaction.response.defer()

        comments = await forum_service.fetch_all_comments(self.client.session)

        new_comments = []
        for comment in comments:
            if await self.client.entities.forum.is_seen(comment.id):
                continue
            await self.client.entities.forum.mark_seen(
                comment.id, comment.thread_id, comment.thread_title, comment.author, comment.text, comment.url
            )
            new_comments.append(comment)

        if not new_comments:
            await interaction.followup.send(view=InfoView("No new forum comments since the last check."))
            return

        heading = "💬 New Boursorama forum comments"
        if len(new_comments) > PAGE_SIZE:
            heading += f" (showing {PAGE_SIZE} of {len(new_comments)})"

        await interaction.followup.send(view=ForumView(new_comments[:PAGE_SIZE], heading=heading))

    @forum_group.command(name="all", description="Browse every previously-seen Boursorama forum comment")
    async def all(self, interaction: Interaction) -> None:
        await interaction.response.defer()

        total = await self.client.entities.forum.count()
        if total == 0:
            await interaction.followup.send(view=InfoView("No forum comments recorded yet. Try /forum latest first."))
            return

        rows = await self.client.entities.forum.list_page(0, PAGE_SIZE)
        comments = [forum_service.ForumComment.from_row(row) for row in rows]

        view = ForumAllView(self.client.entities, page=0, total=total, comments=comments, author_id=interaction.user.id)
        view.message = await interaction.followup.send(view=view, wait=True)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Forum(client))

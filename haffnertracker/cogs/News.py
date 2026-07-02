from discord import Interaction, app_commands
from discord.ext import commands

from ..services import news as news_service
from ..views.info import InfoView
from ..views.news import PAGE_SIZE, NewsAllView, NewsView


class News(commands.Cog):
    def __init__(self, client: commands.Bot) -> None:
        self.client = client

    news_group = app_commands.Group(name="news", description="Haffner Energy news")

    @news_group.command(name="latest", description="Fetch and post the latest Haffner Energy news now")
    @app_commands.checks.cooldown(1, 300, key=lambda i: i.guild_id)
    async def latest(self, interaction: Interaction) -> None:
        await interaction.response.defer()

        articles = await news_service.fetch_all(self.client.session, self.client.newsapi_key)

        new_articles = []
        for article in articles:
            if await self.client.entities.news.is_seen(article.id):
                continue
            await self.client.entities.news.mark_seen(
                article.id, article.title, article.source, article.url, article.published_at
            )
            new_articles.append(article)

        if not new_articles:
            await interaction.followup.send(view=InfoView("No new articles since the last check."))
            return

        heading = "📰 New Haffner Energy news"
        if len(new_articles) > PAGE_SIZE:
            heading += f" (showing {PAGE_SIZE} of {len(new_articles)})"

        await interaction.followup.send(view=NewsView(new_articles[:PAGE_SIZE], heading=heading))

    @news_group.command(name="all", description="Browse every previously-seen Haffner Energy article")
    async def all(self, interaction: Interaction) -> None:
        await interaction.response.defer()

        total = await self.client.entities.news.count()
        if total == 0:
            await interaction.followup.send(view=InfoView("No news recorded yet. Try /news latest first."))
            return

        rows = await self.client.entities.news.list_page(0, PAGE_SIZE)
        articles = [news_service.Article.from_row(row) for row in rows]

        view = NewsAllView(self.client.entities, page=0, total=total, articles=articles, author_id=interaction.user.id)
        view.message = await interaction.followup.send(view=view, wait=True)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(News(client))

import math

from urllib.parse import urlsplit, urlunsplit

import discord

from ..entities.entities import Entities
from ..services.news import Article, parse_published_at
from ..utils.constants import COLOR_NEUTRAL, COLOR_OFFICIAL, OFFICIAL_NEWS_SOURCE
from .info import InfoView

PAGE_SIZE = 5

# Discord rejects button URLs longer than this, and some NewsAPI links carry huge tracking query strings.
MAX_BUTTON_URL_LENGTH = 512


def _safe_article_url(url: str) -> str | None:
    if len(url) <= MAX_BUTTON_URL_LENGTH:
        return url

    stripped = urlunsplit(urlsplit(url)._replace(query="", fragment=""))
    if len(stripped) <= MAX_BUTTON_URL_LENGTH:
        return stripped

    return None


def _is_official(article: Article) -> bool:
    return article.source == OFFICIAL_NEWS_SOURCE


def _article_text(article: Article) -> str:
    published = parse_published_at(article.published_at)
    source_label = f"📣 {article.source}" if _is_official(article) else article.source
    meta = f"-# {source_label} • <t:{int(published.timestamp())}:R>" if published else f"-# {source_label}"

    title = f"**📣 {article.title}**" if _is_official(article) else f"**{article.title}**"
    lines = [title, meta]
    if article.description:
        lines.append(article.description)

    return "\n".join(lines)


def _article_sections(articles: list[Article]) -> list[discord.ui.Item]:
    items: list[discord.ui.Item] = []
    for i, article in enumerate(articles):
        if i > 0:
            items.append(discord.ui.Separator())

        url = _safe_article_url(article.url)
        if url is not None:
            accessory = discord.ui.Button(label="Read", style=discord.ButtonStyle.link, url=url)
        else:
            accessory = discord.ui.Button(label="Read", style=discord.ButtonStyle.secondary, disabled=True)

        items.append(discord.ui.Section(_article_text(article), accessory=accessory))

        if article.image_url:
            items.append(
                discord.ui.MediaGallery(discord.MediaGalleryItem(media=article.image_url, description=article.title))
            )
    return items


def _article_containers(articles: list[Article]) -> list[discord.ui.Container]:
    """Splits articles into runs of consecutive official/non-official items, each its own
    accent-coloured container, so official Haffner Energy updates stand out from press coverage."""
    containers: list[discord.ui.Container] = []
    group: list[Article] = []

    def _flush() -> None:
        if group:
            color = COLOR_OFFICIAL if _is_official(group[0]) else COLOR_NEUTRAL
            containers.append(discord.ui.Container(*_article_sections(group), accent_colour=color))

    for article in articles:
        if group and _is_official(group[0]) != _is_official(article):
            _flush()
            group = []
        group.append(article)
    _flush()

    return containers


class NewsView(discord.ui.LayoutView):
    """A static digest of news articles, used for the /news latest command and the auto-post loop."""

    def __init__(self, articles: list[Article], heading: str = "📰 New Haffner Energy news") -> None:
        super().__init__()

        self.add_item(discord.ui.TextDisplay(f"### {heading}"))
        for container in _article_containers(articles):
            self.add_item(container)


class NewsAllView(discord.ui.LayoutView):
    """A paginated browser over every previously-seen news article, for /news all."""

    def __init__(self, entities: Entities, page: int, total: int, articles: list[Article], author_id: int) -> None:
        super().__init__(timeout=300)

        self.entities = entities
        self.page = page
        self.total = total
        self.total_pages = max(1, math.ceil(total / PAGE_SIZE))
        self.author_id = author_id
        self.message: discord.Message | None = None

        heading = f"### 🗞️ All Haffner Energy news — page {self.page + 1}/{self.total_pages}"
        self.add_item(discord.ui.TextDisplay(heading))
        for container in _article_containers(articles):
            self.add_item(container)
        self.add_item(self._NavigationRow(self))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.author_id:
            return True

        await interaction.response.send_message(
            view=InfoView("Only the person who ran this command can navigate it — run `/news all` yourself to browse."),
            ephemeral=True,
        )
        return False

    class _NavigationRow(discord.ui.ActionRow):
        def __init__(self, paginator: "NewsAllView") -> None:
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
        rows = await self.entities.news.list_page(page * PAGE_SIZE, PAGE_SIZE)
        articles = [Article.from_row(row) for row in rows]

        new_view = NewsAllView(self.entities, page, self.total, articles, self.author_id)
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

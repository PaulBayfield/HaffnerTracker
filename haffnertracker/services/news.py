import hashlib

from dataclasses import dataclass
from html import unescape
from urllib.parse import quote

import feedparser

from aiohttp import ClientSession

from ..utils.constants import (
    GOOGLE_NEWS_RSS_URL,
    NEWS_SEARCH_TERMS,
    NEWSAPI_URL,
    PRESS_RELEASES_API_URL,
)


@dataclass
class Article:
    title: str
    url: str
    source: str
    published_at: str | None

    @property
    def id(self) -> str:
        return hashlib.sha256(self.url.encode()).hexdigest()[:32]

    @classmethod
    def from_row(cls, row) -> "Article":
        return cls(title=row["title"], url=row["url"], source=row["source"], published_at=row["published_at"])


async def fetch_google_news(session: ClientSession) -> list[Article]:
    articles: list[Article] = []

    for term in NEWS_SEARCH_TERMS:
        url = GOOGLE_NEWS_RSS_URL.format(query=quote(term))
        async with session.get(url) as resp:
            if resp.status != 200:
                continue
            body = await resp.text()

        feed = feedparser.parse(body)
        for entry in feed.entries:
            source = getattr(entry, "source", {})
            source_title = source.get("title", "Google News") if isinstance(source, dict) else "Google News"
            articles.append(
                Article(
                    title=entry.title,
                    url=entry.link,
                    source=source_title,
                    published_at=getattr(entry, "published", None),
                )
            )

    return articles


async def fetch_newsapi(session: ClientSession, api_key: str) -> list[Article]:
    if not api_key:
        return []

    params = {
        "q": '"Haffner Energy"',
        "language": "fr",
        "sortBy": "publishedAt",
        "pageSize": "20",
        "apiKey": api_key,
    }

    async with session.get(NEWSAPI_URL, params=params) as resp:
        if resp.status != 200:
            return []
        data = await resp.json()

    return [
        Article(
            title=item["title"],
            url=item["url"],
            source=(item.get("source") or {}).get("name", "NewsAPI"),
            published_at=item.get("publishedAt"),
        )
        for item in data.get("articles", [])
    ]


async def fetch_press_releases(session: ClientSession) -> list[Article]:
    params = {"per_page": "10", "_fields": "id,link,date,title"}

    async with session.get(PRESS_RELEASES_API_URL, params=params) as resp:
        if resp.status != 200:
            return []
        data = await resp.json()

    return [
        Article(
            title=unescape(item["title"]["rendered"]),
            url=item["link"],
            source="Haffner Energy Newsroom",
            published_at=item.get("date"),
        )
        for item in data
    ]


async def fetch_all(session: ClientSession, newsapi_key: str) -> list[Article]:
    google = await fetch_google_news(session)
    newsapi = await fetch_newsapi(session, newsapi_key)
    press = await fetch_press_releases(session)

    seen_ids: set[str] = set()
    merged: list[Article] = []
    for article in [*press, *google, *newsapi]:
        if article.id in seen_ids:
            continue
        seen_ids.add(article.id)
        merged.append(article)

    return merged

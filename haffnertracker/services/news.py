import asyncio
import hashlib
import logging
import re

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from urllib.parse import quote

import feedparser

from aiohttp import ClientSession

from ..utils.constants import (
    GOOGLE_NEWS_RSS_URL,
    MAX_NEWS_AGE_DAYS,
    NEWS_SEARCH_TERMS,
    NEWSAPI_URL,
    PRESS_RELEASES_API_URL,
)

logger = logging.getLogger(__name__)


@dataclass
class Article:
    title: str
    url: str
    source: str
    published_at: str | None
    description: str | None = None
    image_url: str | None = None

    @property
    def id(self) -> str:
        return hashlib.sha256(self.url.encode()).hexdigest()[:32]

    @classmethod
    def from_row(cls, row) -> "Article":
        return cls(
            title=row["title"],
            url=row["url"],
            source=row["source"],
            published_at=row["published_at"],
            description=row["description"] if "description" in row.keys() else None,
            image_url=row["image_url"] if "image_url" in row.keys() else None,
        )


_HTML_TAG_RE = re.compile(r"<[^>]+>")

DESCRIPTION_MAX_LENGTH = 220


def _clean_html(html: str | None) -> str | None:
    if not html:
        return None

    text = unescape(_HTML_TAG_RE.sub("", html)).strip()
    return text or None


def _truncate(text: str | None, max_length: int = DESCRIPTION_MAX_LENGTH) -> str | None:
    if not text:
        return None

    if len(text) <= max_length:
        return text

    return text[: max_length - 1].rstrip() + "…"


def parse_published_at(published_at: str | None) -> datetime | None:
    if not published_at:
        return None

    try:
        dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
    except ValueError:
        try:
            dt = parsedate_to_datetime(published_at)
        except (TypeError, ValueError):
            return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def is_recent(article: Article, max_age_days: int = MAX_NEWS_AGE_DAYS) -> bool:
    published = parse_published_at(article.published_at)
    if published is None:
        return True

    return datetime.now(timezone.utc) - published <= timedelta(days=max_age_days)


async def _fetch_google_news_term(session: ClientSession, term: str) -> list[Article]:
    articles: list[Article] = []

    url = GOOGLE_NEWS_RSS_URL.format(query=quote(term))
    async with session.get(url) as resp:
        if resp.status != 200:
            return articles
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


async def fetch_google_news(session: ClientSession) -> list[Article]:
    results = await asyncio.gather(
        *(_fetch_google_news_term(session, term) for term in NEWS_SEARCH_TERMS),
        return_exceptions=True,
    )

    articles: list[Article] = []
    for term, result in zip(NEWS_SEARCH_TERMS, results):
        if isinstance(result, BaseException):
            logger.warning("Google News fetch failed for term %r: %r", term, result)
            continue
        articles.extend(result)

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
            description=_truncate(item.get("description")),
            image_url=item.get("urlToImage") or None,
        )
        for item in data.get("articles", [])
    ]


async def fetch_press_releases(session: ClientSession) -> list[Article]:
    params = {"per_page": "10", "_fields": "id,link,date,title,excerpt,yoast_head_json"}

    async with session.get(PRESS_RELEASES_API_URL, params=params) as resp:
        if resp.status != 200:
            return []
        data = await resp.json()

    articles = []
    for item in data:
        yoast = item.get("yoast_head_json") or {}
        og_images = yoast.get("og_image") or []
        image_url = og_images[0].get("url") if og_images else None

        excerpt = _clean_html((item.get("excerpt") or {}).get("rendered"))
        description = _truncate(excerpt or yoast.get("og_description") or yoast.get("description"))

        articles.append(
            Article(
                title=unescape(item["title"]["rendered"]),
                url=item["link"],
                source="Haffner Energy Newsroom",
                published_at=item.get("date"),
                description=description,
                image_url=image_url,
            )
        )

    return articles


async def fetch_all(session: ClientSession, newsapi_key: str) -> list[Article]:
    sources = (
        ("google", fetch_google_news(session)),
        ("newsapi", fetch_newsapi(session, newsapi_key)),
        ("press releases", fetch_press_releases(session)),
    )
    results = await asyncio.gather(*(coro for _, coro in sources), return_exceptions=True)

    press: list[Article] = []
    google: list[Article] = []
    newsapi: list[Article] = []
    for (name, _), result in zip(sources, results):
        if isinstance(result, BaseException):
            logger.warning("News fetch failed for source %r: %r", name, result)
            continue
        if name == "press releases":
            press = result
        elif name == "google":
            google = result
        else:
            newsapi = result

    seen_ids: set[str] = set()
    merged: list[Article] = []
    for article in [*press, *google, *newsapi]:
        if article.id in seen_ids:
            continue
        if not is_recent(article):
            continue
        seen_ids.add(article.id)
        merged.append(article)

    return merged

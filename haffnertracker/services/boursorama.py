import asyncio
import logging

from dataclasses import dataclass
from urllib.parse import urljoin

from aiohttp import ClientSession
from bs4 import BeautifulSoup

from ..utils.constants import BOURSORAMA_FORUM_URL, FORUM_MAX_THREADS_PER_POLL

logger = logging.getLogger(__name__)

TEXT_MAX_LENGTH = 500

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; HaffnerTracker/1.0)"}


@dataclass
class ForumThread:
    id: str
    title: str
    url: str


@dataclass
class ForumComment:
    id: str
    thread_id: str
    thread_title: str
    author: str
    text: str
    url: str

    @classmethod
    def from_row(cls, row) -> "ForumComment":
        return cls(
            id=row["id"],
            thread_id=row["thread_id"],
            thread_title=row["thread_title"],
            author=row["author"],
            text=row["text"],
            url=row["url"],
        )


def _truncate(text: str, max_length: int = TEXT_MAX_LENGTH) -> str:
    if len(text) <= max_length:
        return text

    return text[: max_length - 1].rstrip() + "…"


async def fetch_active_threads(session: ClientSession) -> list[ForumThread]:
    async with session.get(BOURSORAMA_FORUM_URL, headers=HEADERS) as resp:
        if resp.status != 200:
            return []
        body = await resp.text()

    soup = BeautifulSoup(body, "html.parser")

    threads: list[ForumThread] = []
    seen_ids: set[str] = set()
    for link in soup.select("a[href*='/detail/']"):
        href = link.get("href")
        title = link.get_text(strip=True)
        if not href or not title:
            continue

        thread_id = href.rstrip("/").rsplit("/", 1)[-1]
        if not thread_id.isdigit() or thread_id in seen_ids:
            continue

        seen_ids.add(thread_id)
        threads.append(ForumThread(id=thread_id, title=title, url=urljoin(BOURSORAMA_FORUM_URL, href)))

        if len(threads) >= FORUM_MAX_THREADS_PER_POLL:
            break

    return threads


async def fetch_thread_comments(session: ClientSession, thread: ForumThread) -> list[ForumComment]:
    async with session.get(thread.url, headers=HEADERS) as resp:
        if resp.status != 200:
            return []
        body = await resp.text()

    soup = BeautifulSoup(body, "html.parser")

    comments: list[ForumComment] = []
    for message in soup.select("div.c-message[id]"):
        message_id = message.get("id")
        if not message_id:
            continue

        text_tag = message.select_one("p.c-message__text")
        text = text_tag.get_text(separator="\n", strip=True) if text_tag else ""
        if not text:
            continue

        author_tag = message.select_one(".c-profile-card__name")
        author = author_tag.get_text(strip=True) if author_tag else "Anonyme"

        comments.append(
            ForumComment(
                id=message_id,
                thread_id=thread.id,
                thread_title=thread.title,
                author=author,
                text=_truncate(text),
                url=f"{thread.url}#{message_id}",
            )
        )

    return comments


async def fetch_all_comments(session: ClientSession) -> list[ForumComment]:
    threads = await fetch_active_threads(session)

    results = await asyncio.gather(
        *(fetch_thread_comments(session, thread) for thread in threads),
        return_exceptions=True,
    )

    comments: list[ForumComment] = []
    for thread, result in zip(threads, results):
        if isinstance(result, BaseException):
            logger.warning("Forum fetch failed for thread %r: %r", thread.id, result)
            continue
        comments.extend(result)

    return comments

from datetime import datetime, timedelta, timezone

from haffnertracker.services.news import (
    Article,
    _clean_html,
    _truncate,
    fetch_all,
    is_recent,
    parse_published_at,
)


def _article(published_at: str | None, url: str = "https://example.com/a") -> Article:
    return Article(title="t", url=url, source="s", published_at=published_at)


class TestParsePublishedAt:
    def test_parses_iso8601_with_z_suffix(self):
        dt = parse_published_at("2026-07-05T12:00:00Z")
        assert dt == datetime(2026, 7, 5, 12, 0, 0, tzinfo=timezone.utc)

    def test_parses_iso8601_without_timezone_as_utc(self):
        dt = parse_published_at("2026-07-10T08:30:00")
        assert dt == datetime(2026, 7, 10, 8, 30, 0, tzinfo=timezone.utc)

    def test_parses_rfc822_rss_dates(self):
        dt = parse_published_at("Wed, 02 Jul 2025 12:00:00 GMT")
        assert dt == datetime(2025, 7, 2, 12, 0, 0, tzinfo=timezone.utc)

    def test_returns_none_for_missing_or_unparseable_input(self):
        assert parse_published_at(None) is None
        assert parse_published_at("") is None
        assert parse_published_at("garbage-date") is None


class TestIsRecent:
    def test_keeps_articles_within_the_age_window(self):
        recent = datetime.now(timezone.utc) - timedelta(days=1)
        article = _article(recent.isoformat())
        assert is_recent(article, max_age_days=7) is True

    def test_drops_articles_older_than_the_age_window(self):
        old = datetime.now(timezone.utc) - timedelta(days=30)
        article = _article(old.isoformat())
        assert is_recent(article, max_age_days=7) is False

    def test_keeps_articles_with_unknown_dates_rather_than_hiding_them(self):
        article = _article(None)
        assert is_recent(article, max_age_days=7) is True


class TestCleanHtmlAndTruncate:
    def test_strips_tags_and_unescapes_entities(self):
        assert _clean_html("<p>Hello&nbsp;&amp; welcome</p>") == "Hello\xa0& welcome"

    def test_returns_none_for_empty_input(self):
        assert _clean_html(None) is None
        assert _clean_html("") is None
        assert _clean_html("<p></p>") is None

    def test_truncate_leaves_short_text_untouched(self):
        assert _truncate("short", max_length=10) == "short"

    def test_truncate_adds_ellipsis_for_long_text(self):
        result = _truncate("a" * 50, max_length=10)
        assert result == "a" * 9 + "…"
        assert len(result) == 10

    def test_truncate_returns_none_for_empty_input(self):
        assert _truncate(None) is None


class TestFetchAll:
    async def test_dedupes_by_url_and_filters_out_old_articles(self, monkeypatch):
        recent = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        old = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()

        duplicate_url = "https://example.com/duplicate"
        press = [Article("Press release", duplicate_url, "Newsroom", recent)]
        google = [
            Article("Duplicate via Google", duplicate_url, "Google News", recent),
            Article("Too old", "https://example.com/old", "Google News", old),
        ]
        newsapi = [Article("Fresh NewsAPI hit", "https://example.com/fresh", "NewsAPI", recent)]

        async def fake_google(session):
            return google

        async def fake_newsapi(session, api_key):
            return newsapi

        async def fake_press(session):
            return press

        monkeypatch.setattr("haffnertracker.services.news.fetch_google_news", fake_google)
        monkeypatch.setattr("haffnertracker.services.news.fetch_newsapi", fake_newsapi)
        monkeypatch.setattr("haffnertracker.services.news.fetch_press_releases", fake_press)

        articles = await fetch_all(session=None, newsapi_key="key")

        urls = [a.url for a in articles]
        assert urls == ["https://example.com/duplicate", "https://example.com/fresh"]

    async def test_one_source_failing_does_not_prevent_others_from_being_returned(self, monkeypatch):
        recent = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        newsapi = [Article("Fresh NewsAPI hit", "https://example.com/fresh", "NewsAPI", recent)]

        async def fake_google(session):
            raise RuntimeError("boom")

        async def fake_newsapi(session, api_key):
            return newsapi

        async def fake_press(session):
            return []

        monkeypatch.setattr("haffnertracker.services.news.fetch_google_news", fake_google)
        monkeypatch.setattr("haffnertracker.services.news.fetch_newsapi", fake_newsapi)
        monkeypatch.setattr("haffnertracker.services.news.fetch_press_releases", fake_press)

        articles = await fetch_all(session=None, newsapi_key="key")

        assert [a.url for a in articles] == ["https://example.com/fresh"]


def test_article_id_is_stable_and_url_specific():
    a = Article("t", "https://example.com/a", "s", None)
    b = Article("different title", "https://example.com/a", "different source", None)
    c = Article("t", "https://example.com/b", "s", None)

    assert a.id == b.id
    assert a.id != c.id

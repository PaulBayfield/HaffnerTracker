from haffnertracker.services.news import Article
from haffnertracker.utils.constants import COLOR_NEUTRAL, COLOR_OFFICIAL, OFFICIAL_NEWS_SOURCE
from haffnertracker.views.news import _article_containers, _article_text


def _article(source: str, url: str = "https://example.com/a") -> Article:
    return Article(title="Some title", url=url, source=source, published_at=None)


class TestArticleContainers:
    def test_single_source_batch_produces_one_container(self):
        articles = [_article("Google News"), _article("Google News", "https://example.com/b")]
        containers = _article_containers(articles)

        assert len(containers) == 1
        assert containers[0].accent_colour == COLOR_NEUTRAL

    def test_official_articles_get_their_own_gold_container(self):
        articles = [_article(OFFICIAL_NEWS_SOURCE)]
        containers = _article_containers(articles)

        assert len(containers) == 1
        assert containers[0].accent_colour == COLOR_OFFICIAL

    def test_mixed_sources_split_into_separate_containers_in_order(self):
        articles = [
            _article(OFFICIAL_NEWS_SOURCE, "https://example.com/1"),
            _article("Google News", "https://example.com/2"),
            _article(OFFICIAL_NEWS_SOURCE, "https://example.com/3"),
        ]
        containers = _article_containers(articles)

        assert [c.accent_colour for c in containers] == [COLOR_OFFICIAL, COLOR_NEUTRAL, COLOR_OFFICIAL]

    def test_empty_articles_produce_no_containers(self):
        assert _article_containers([]) == []


class TestArticleText:
    def test_official_articles_get_a_badge(self):
        text = _article_text(_article(OFFICIAL_NEWS_SOURCE))
        assert "📣" in text

    def test_non_official_articles_have_no_badge(self):
        text = _article_text(_article("Google News"))
        assert "📣" not in text

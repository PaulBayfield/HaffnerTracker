from haffnertracker.services.boursorama import (
    ForumComment,
    ForumThread,
    _parse_french_number,
    _truncate,
    fetch_active_threads,
    fetch_all_comments,
    fetch_quote,
    fetch_thread_comments,
    parse_quote,
)

THREAD_LIST_HTML = """
<table>
<tr><td><a href="/bourse/forum/1rPALHAF/detail/111111/" class="c-link">Premier sujet</a></td></tr>
<tr><td><a href="/bourse/forum/1rPALHAF/detail/111111/" class="c-link">Premier sujet</a></td></tr>
<tr><td><a href="/bourse/forum/1rPALHAF/detail/222222/" class="c-link">Deuxième sujet</a></td></tr>
</table>
"""

THREAD_DETAIL_HTML = """
<div class="c-message" id="111111">
    <div class="c-profile-card__name"><button>ref1929</button></div>
    <p class="c-message__text">Info issue de 2CRSI.<br/>Haffner accumule des contrats.</p>
</div>
<div class="c-message" id="111112">
    <div class="c-profile-card__name"><button>joella</button></div>
    <p class="c-message__text">Merci pour l'info</p>
</div>
<div class="c-message" id="111113">
    <div class="c-profile-card__name"><button>ghost</button></div>
    <p class="c-message__text"></p>
</div>
"""


class _FakeResponse:
    def __init__(self, status: int, body: str) -> None:
        self.status = status
        self._body = body

    async def text(self) -> str:
        return self._body

    async def __aenter__(self) -> "_FakeResponse":
        return self

    async def __aexit__(self, *exc) -> bool:
        return False


class _FakeSession:
    def __init__(self, responses: dict[str, str]) -> None:
        self._responses = responses

    def get(self, url, headers=None):
        return _FakeResponse(200, self._responses[url])


class TestTruncate:
    def test_leaves_short_text_untouched(self):
        assert _truncate("short", max_length=10) == "short"

    def test_adds_ellipsis_for_long_text(self):
        result = _truncate("a" * 50, max_length=10)
        assert result == "a" * 9 + "…"
        assert len(result) == 10


class TestFetchActiveThreads:
    async def test_parses_thread_rows_and_dedupes_by_id(self):
        session = _FakeSession({"https://www.boursorama.com/bourse/forum/1rPALHAF/": THREAD_LIST_HTML})

        threads = await fetch_active_threads(session)

        assert [t.id for t in threads] == ["111111", "222222"]
        assert threads[0].title == "Premier sujet"
        assert threads[0].url == "https://www.boursorama.com/bourse/forum/1rPALHAF/detail/111111/"

    async def test_respects_max_threads_per_poll(self, monkeypatch):
        monkeypatch.setattr("haffnertracker.services.boursorama.FORUM_MAX_THREADS_PER_POLL", 1)
        session = _FakeSession({"https://www.boursorama.com/bourse/forum/1rPALHAF/": THREAD_LIST_HTML})

        threads = await fetch_active_threads(session)

        assert len(threads) == 1


class TestFetchThreadComments:
    async def test_parses_messages_and_skips_empty_ones(self):
        thread = ForumThread(id="111111", title="Premier sujet", url="https://example.com/detail/111111/")
        session = _FakeSession({thread.url: THREAD_DETAIL_HTML})

        comments = await fetch_thread_comments(session, thread)

        assert [c.id for c in comments] == ["111111", "111112"]
        assert comments[0].author == "ref1929"
        assert comments[0].text == "Info issue de 2CRSI.\nHaffner accumule des contrats."
        assert comments[0].thread_title == "Premier sujet"
        assert comments[0].url == "https://example.com/detail/111111/#111111"


class TestFetchAllComments:
    async def test_aggregates_comments_across_threads_and_survives_a_failing_thread(self, monkeypatch):
        threads = [
            ForumThread(id="1", title="A", url="https://example.com/a"),
            ForumThread(id="2", title="B", url="https://example.com/b"),
        ]

        async def fake_threads(session):
            return threads

        async def fake_comments(session, thread):
            if thread.id == "2":
                raise RuntimeError("boom")
            return [
                ForumComment(
                    id="c1", thread_id="1", thread_title="A", author="x", text="hi", url="https://example.com/a#c1"
                )
            ]

        monkeypatch.setattr("haffnertracker.services.boursorama.fetch_active_threads", fake_threads)
        monkeypatch.setattr("haffnertracker.services.boursorama.fetch_thread_comments", fake_comments)

        comments = await fetch_all_comments(session=None)

        assert [c.id for c in comments] == ["c1"]


QUOTE_HTML = """
<div class="c-ticker__item" data-ist="1rPCAC"><span data-ist-last>8 092,28</span></div>
<div class="c-faceplate is-negative" data-faceplate data-ist="1rPALHAF"
     data-ist-init='{"symbol":"1rPALHAF","high":0.794,"low":0.74,"previousClose":0.79,"totalVolume":2747660,
                     "tradeDate":"2026-09-25 09:58:32","last":0.788}'>
    <span class="c-instrument c-instrument--last" data-ist-last>0,7880</span>
    <span class="c-instrument c-instrument--open" data-ist-open>0,7600</span>
</div>
"""


class TestParseFrenchNumber:
    def test_handles_thousands_spaces_and_decimal_comma(self):
        assert _parse_french_number("2 747 660") == 2747660
        assert _parse_french_number("0,7880") == 0.788
        assert _parse_french_number("8 092,28") == 8092.28

    def test_returns_none_for_garbage(self):
        assert _parse_french_number("--") is None


class TestParseQuote:
    def test_reads_the_haffner_faceplate_and_ignores_other_instruments(self):
        quote = parse_quote(QUOTE_HTML)

        assert quote is not None
        assert quote.price == 0.788
        assert quote.previous_close == 0.79
        assert quote.open == 0.76
        assert quote.high == 0.794
        assert quote.low == 0.74
        assert quote.volume == 2747660
        assert quote.source == "Boursorama"
        assert quote.traded_at.isoformat() == "2026-09-25T09:58:32+02:00"
        assert round(quote.change_pct, 2) == -0.25

    def test_returns_none_when_faceplate_is_missing(self):
        assert parse_quote("<html><body>Maintenance</body></html>") is None

    def test_returns_none_when_init_json_is_broken(self):
        html = """<div class="c-faceplate" data-ist="1rPALHAF" data-ist-init='{"last":'></div>"""
        assert parse_quote(html) is None


class TestFetchQuote:
    async def test_fetches_and_parses_the_quote_page(self):
        session = _FakeSession({"https://www.boursorama.com/cours/1rPALHAF/": QUOTE_HTML})

        quote = await fetch_quote(session)

        assert quote.price == 0.788

from datetime import datetime, timedelta, timezone

import pandas as pd

from haffnertracker.services import stock


def _hist(timestamps: list[datetime]) -> pd.DataFrame:
    return pd.DataFrame({"Close": [float(i) for i in range(len(timestamps))]}, index=pd.DatetimeIndex(timestamps))


class TestGetChartHistory:
    async def test_uses_the_configured_yfinance_period_and_interval(self, monkeypatch):
        captured = {}

        async def fake_get_history(period, interval):
            captured["period"] = period
            captured["interval"] = interval
            return _hist([datetime.now(timezone.utc)])

        monkeypatch.setattr(stock, "get_history", fake_get_history)

        await stock.get_chart_history("6h")

        assert captured == {"period": "5d", "interval": "5m"}

    async def test_trims_to_the_trailing_window_relative_to_the_latest_bar(self, monkeypatch):
        now = datetime(2026, 7, 31, 12, 0, tzinfo=timezone.utc)
        timestamps = [now - timedelta(hours=h) for h in (30, 10, 5, 1, 0)]

        async def fake_get_history(period, interval):
            return _hist(timestamps)

        monkeypatch.setattr(stock, "get_history", fake_get_history)

        hist = await stock.get_chart_history("6h")

        assert len(hist) == 3
        assert hist.index.min() == now - timedelta(hours=5)

    async def test_ranges_without_a_window_return_everything_fetched(self, monkeypatch):
        timestamps = [datetime(2026, 1, d, tzinfo=timezone.utc) for d in (1, 2, 3)]

        async def fake_get_history(period, interval):
            return _hist(timestamps)

        monkeypatch.setattr(stock, "get_history", fake_get_history)

        hist = await stock.get_chart_history("1mo")

        assert len(hist) == 3

    async def test_empty_history_is_returned_untouched(self, monkeypatch):
        async def fake_get_history(period, interval):
            return _hist([])

        monkeypatch.setattr(stock, "get_history", fake_get_history)

        hist = await stock.get_chart_history("1d")

        assert hist.empty

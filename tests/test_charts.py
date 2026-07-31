from datetime import datetime, timedelta

from haffnertracker.utils.charts import _date_format


class TestDateFormat:
    def test_intraday_span_uses_time_only(self):
        dates = [datetime(2026, 7, 31, 9, 0), datetime(2026, 7, 31, 15, 0)]
        assert _date_format(dates) == "%H:%M"

    def test_multi_day_span_includes_date_and_hour(self):
        dates = [datetime(2026, 7, 25, 9, 0), datetime(2026, 7, 31, 15, 0)]
        assert _date_format(dates) == "%d %b %Hh"

    def test_long_span_uses_date_only(self):
        dates = [datetime(2026, 1, 1), datetime(2026, 7, 31)]
        assert _date_format(dates) == "%d %b"

    def test_span_boundary_of_exactly_one_day_stays_time_only(self):
        dates = [datetime(2026, 7, 30, 12, 0), datetime(2026, 7, 31, 12, 0) - timedelta(seconds=1)]
        assert _date_format(dates) == "%H:%M"

from datetime import timedelta
from io import BytesIO


def _date_format(dates: list) -> str:
    """Picks a tighter x-axis format for intraday ranges, since "%d %b" alone would repeat
    the same day label across every point."""
    span = dates[-1] - dates[0]
    if span <= timedelta(days=1):
        return "%H:%M"
    if span <= timedelta(days=8):
        return "%d %b %Hh"
    return "%d %b"


def render_price_chart(dates: list, closes: list) -> BytesIO:
    """Render a price history line chart to a PNG buffer."""
    import matplotlib

    matplotlib.use("Agg")

    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150)

    color = "#2ecc71" if closes[-1] >= closes[0] else "#e74c3c"
    ax.plot(dates, closes, color=color, linewidth=1.75)
    ax.fill_between(dates, closes, min(closes) * 0.995, color=color, alpha=0.1)

    ax.set_ylabel("EUR")
    ax.grid(True, alpha=0.25)
    ax.xaxis.set_major_formatter(mdates.DateFormatter(_date_format(dates)))
    fig.autofmt_xdate()

    buf = BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)

    return buf

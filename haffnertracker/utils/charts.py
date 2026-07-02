from io import BytesIO

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt


def render_price_chart(dates: list, closes: list) -> BytesIO:
    """Render a price history line chart to a PNG buffer."""
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150)

    color = "#2ecc71" if closes[-1] >= closes[0] else "#e74c3c"
    ax.plot(dates, closes, color=color, linewidth=1.75)
    ax.fill_between(dates, closes, min(closes) * 0.995, color=color, alpha=0.1)

    ax.set_ylabel("EUR")
    ax.grid(True, alpha=0.25)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    fig.autofmt_xdate()

    buf = BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)

    return buf

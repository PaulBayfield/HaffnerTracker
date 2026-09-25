from dataclasses import dataclass
from datetime import datetime


@dataclass
class Quote:
    price: float
    previous_close: float
    currency: str
    source: str = "Yahoo Finance"
    open: float | None = None
    high: float | None = None
    low: float | None = None
    volume: int | None = None
    traded_at: datetime | None = None

    @property
    def change(self) -> float:
        return self.price - self.previous_close

    @property
    def change_pct(self) -> float:
        if self.previous_close == 0:
            return 0.0
        return (self.change / self.previous_close) * 100

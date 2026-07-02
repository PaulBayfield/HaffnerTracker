import aiosqlite

from .alerts import Alerts
from .guild_config import GuildConfig
from .news import News
from .prices import Prices


class Entities:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db
        self.prices = Prices(db)
        self.news = News(db)
        self.alerts = Alerts(db)
        self.guild_config = GuildConfig(db)

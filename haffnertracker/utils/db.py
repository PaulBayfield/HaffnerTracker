from pathlib import Path

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS price_history (
    date TEXT PRIMARY KEY,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS seen_news (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    source TEXT NOT NULL,
    url TEXT NOT NULL,
    published_at TEXT,
    posted_at TEXT NOT NULL,
    description TEXT,
    image_url TEXT
);

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    guild_id INTEGER NOT NULL,
    kind TEXT NOT NULL,
    threshold REAL NOT NULL,
    created_at TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS guild_config (
    guild_id INTEGER PRIMARY KEY,
    news_channel_id INTEGER,
    price_channel_id INTEGER
);
"""


async def connect(path: str) -> aiosqlite.Connection:
    """Open the sqlite database, creating parent dirs and schema as needed."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    db = await aiosqlite.connect(path)
    db.row_factory = aiosqlite.Row

    await db.executescript(SCHEMA)
    await _migrate(db)
    await db.commit()

    return db


async def _migrate(db: aiosqlite.Connection) -> None:
    """Add columns introduced after a database was first created."""
    cursor = await db.execute("PRAGMA table_info(seen_news)")
    columns = {row["name"] for row in await cursor.fetchall()}

    if "description" not in columns:
        await db.execute("ALTER TABLE seen_news ADD COLUMN description TEXT")
    if "image_url" not in columns:
        await db.execute("ALTER TABLE seen_news ADD COLUMN image_url TEXT")

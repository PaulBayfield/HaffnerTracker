<div align="center">

# HaffnerTracker
A Discord bot for keeping an eye on [Haffner Energy](https://www.haffner-energy.com/) (Euronext Growth Paris, `ALHAF.PA`). Built for a small group of friends who invested together and want news, sector coverage, and stock price history in one place, plus alerts when it's time to pay attention.

</div>

# 📖 • Summary

- [🚀 • Overview](#--overview)
- [✨ • Features](#--features)
- [⚙️ • Setup](#--setup)
- [📄 • Notes](#--notes)
- [📃 • Credits](#--credits)
- [📝 • License](#--license)

# 🚀 • Overview

This repository contains the source code of the HaffnerTracker Discord bot. It's written in Python and uses the [discord.py](https://github.com/Rapptz/discord.py) library, with Discord's newer Components V2 powering every message the bot sends.

News comes from Google News RSS, NewsAPI.org (optional), and Haffner Energy's own newsroom (through its WordPress REST API). LinkedIn and Twitter/X aren't wired up, since neither has a free API that's viable or safe under their terms of service. Stock data comes from Yahoo Finance via `yfinance`, with history kept locally in SQLite so the bot has its own record even if the source changes.

# ✨ • Features

- `/price`: current price and daily change.
- `/chart [period]`: a price chart (`1w`, `1mo`, `3mo`, `1y`, `all`) rendered from locally-stored history.
- `/news latest`: fetches the latest news right now (this also happens automatically every 30 minutes).
- `/news all`: browse every article the bot has ever seen, with a paginated Previous/Next view.
- `/alert set <kind> <threshold>`: get a DM when the price crosses a threshold you pick. `kind` is one of `price_above`, `price_below`, or `pct_change` (a daily move of at least X%).
- `/alert list`, `/alert remove <id>`: manage your alerts.
- `/setnewschannel`, `/setpricechannel`: admin commands to choose which channel news gets posted to.

# ⚙️ • Setup

### 1. Create the Discord bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) and click **New Application**.
2. Under **Bot**, click **Reset Token** and copy it. You'll only see it once.
3. Also under **Bot**, disable "Public Bot" if you don't want strangers adding it to their own servers.
4. Under **OAuth2 → URL Generator**, select the `bot` and `applications.commands` scopes, plus the `Send Messages`, `Embed Links`, `Attach Files`, and `Use Slash Commands` permissions. Open the generated URL to invite the bot to your test server.

### 2. Configure

```
uv sync
cp .env.example .env
```

Fill in `.env`:
- `TOKEN`: the bot token from step 1.
- `OWNER_ID`: your Discord user ID (turn on Developer Mode in Discord settings, then right-click your name and Copy User ID). This grants you the `sync` command.
- `NEWSAPI_KEY`: optional, from [newsapi.org](https://newsapi.org/register) (free tier works fine). News still works without it.

### 3. Run

```
uv run __main__.py
```

On first boot the bot backfills about 5 years of price history into `data/haffnertracker.db`, then keeps it updated from there.

Slash commands won't show up until they're synced. In your server, mention the bot and say `sync`:

```
@HaffnerTracker sync
```

This only works for the account matching `OWNER_ID`. Global command sync can technically take up to an hour to propagate, though in practice it's usually much faster.

Then, in whichever channel you want automatic updates, run:

```
/setnewschannel #news
```

### 4. Docker

```
docker build -t haffnertracker .
docker run -d --env-file .env -v ./data:/app/data haffnertracker
```

There's also a GitHub Actions workflow ([.github/workflows/deployment.yaml](.github/workflows/deployment.yaml)) that builds and publishes the image to GHCR on every push to `main`.

# 📄 • Notes

- Price data comes from Yahoo Finance via `yfinance`, which is free and needs no API key. `ALHAF.PA` is a thinly-traded small cap, so expect some quote latency.
- Price alerts are one-shot. Once triggered they deactivate automatically, so set a new one if you want another.
- This isn't investment advice. The bot surfaces information; it doesn't make buy or sell decisions for you.

# 📃 • Credits

- [Paul Bayfield](https://github.com/PaulBayfield), project founder and lead developer

# 📝 • License

HaffnerTracker is licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details.

```
Copyright 2026 - Paul Bayfield

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```
# Architecture

trailbot is small on purpose: one web process, one database, one external API.

| Piece | Where | What it does |
|---|---|---|
| Webhook (`bot/main.py`) | VPS, uvicorn behind a reverse proxy | Receives Telegram updates, drops repeats, dispatches commands |
| Handlers (`bot/handlers/`) | same process | One file per command |
| Recommender (`bot/recommend.py`) | same process | Scores and ranks trails |
| Weather client (`bot/weather.py`) | same process | Open-Meteo forecasts, cached for 30 minutes |
| PostgreSQL | managed service | Users, trails and ratings |

## How an update flows

1. Telegram posts the update to `/telegram/webhook`.
2. If its `update_id` was already handled, we answer 200 and stop (Telegram retries slow calls).
3. The dispatcher picks the handler from the first word of the message.
4. `/today` loads the trails near the user's home area, gets a forecast per trail and ranks them
   ([SCORING.md](SCORING.md)).
5. The handler replies through the Bot API.

The tables are described in [DATA.md](DATA.md); how it runs in production, in [DEPLOY.md](DEPLOY.md).

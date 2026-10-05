# trailbot — instructions for Claude

trailbot is a Telegram bot that suggests a hike for today, given the weather, the distance and how fit the user
says they are. Everything in this project is in English: code, commits, pull requests and notes.

## Stack
- Python 3.12, a FastAPI webhook (`bot/main.py`), PostgreSQL, Open-Meteo for the forecast.
- Tests: `pytest -q`. Lint: `ruff check .`.

## Pull requests
Keep every pull request small: one change, with its tests, and a description that says what was wrong and why the
change fixes it. Run `pytest -q` and `ruff check .` before asking for review. Never mix a refactor with a behaviour
change in the same pull request. If a test is flaky, fix it or skip it with a reason in the same pull request; never
retry it until it passes.

## Rules
- Never store a user's location history: only the home area they choose.
- `/stop` deletes everything we know about the user, ratings included.
- Secrets live in the environment file on the VPS; never in the repo or in notes.

## Docs
- [Architecture](docs/ARCHITECTURE.md) — the pieces and how an update flows through them.
- [Scoring](docs/SCORING.md) — how trails are ranked.
- [Commands](docs/COMMANDS.md) — what users can type.
- [Data](docs/DATA.md) — the trail seed and the database tables.
- [Deploy](docs/DEPLOY.md) — the VPS, systemd and rollbacks.
- [Privacy](docs/PRIVACY.md) — what we store and for how long.
- [Runbook](docs/RUNBOOK.md) — what to do when something breaks.
- [Contributing trails](docs/CONTRIBUTING.md) — how to add a trail to the seed.
- Decisions: [Telegram first](docs/adr/0001-telegram-first.md), [Open-Meteo](docs/adr/0002-open-meteo.md),
  [Postgres](docs/adr/0003-postgres.md).

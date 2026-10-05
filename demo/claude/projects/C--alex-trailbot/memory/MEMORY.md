# trailbot memory

Memory for chats that start in `proyectos/trailbot`. Everything here is in English.

## Alex and how to work
- [Alex's profile](alex-profile.md) — writes trailbot in English to practise; short answers with file and line
- [Small pull requests](small-prs.md) — one change per pull request, with tests and the why
- [English only](english-only.md) — code, commits and notes in English, even when Alex writes in Spanish
- [Privacy rules](privacy-rules.md) — hashed user ids, no location history, /stop forgets everything

## Product
- [What trailbot does](what-trailbot-does.md) — a hike for today, picked by weather, distance and fitness
- [Trail scoring](trail-scoring.md) — how `recommend.py` ranks trails and why hard trails need fitness
- [Weather provider](weather-provider.md) — Open-Meteo: no key, daily forecast, cached for half an hour
- [Trail data](trail-data.md) — the seed in `data/trails.csv`, who curates it and the `trail_routes` table
- [Telegram commands](telegram-commands.md) — /today, /near, /rate, /stop and /help
- [Deploy](deploy.md) — VPS with systemd, releases side by side, rollback in one command

## Fixes
- [Fix: timezone in forecasts](fix-timezone.md) — forecasts were for the wrong day after 9 pm
- [Fix: duplicate messages](fix-duplicate-messages.md) — Telegram retries made /today answer twice
- [Fix: rating spam](fix-rating-spam.md) — one rating per user, per trail, per day

## Plans
- [Launch checklist](launch-checklist.md) — what is left before the public launch
- [Ideas backlog](ideas-backlog.md) — Strava import, group hikes, offline maps
- [Old roadmap](old-roadmap.md) — the first plan, before the Telegram decision

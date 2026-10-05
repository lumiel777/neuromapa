# Data

## The seed

`data/trails.csv` is curated by hand. Columns: `slug`, `name`, `difficulty` (easy, moderate, hard), `km`, `lat` and
`lon` of the trailhead, and `province`. How to add a trail: [CONTRIBUTING.md](CONTRIBUTING.md).

## Tables

- `trail_routes`: the seed, loaded on every deploy with an upsert by `slug`.
- `trail_ratings`: one row per user, trail and day (unique index), with the stars.
- `users`: the salted hash of the Telegram id, the home area and the fitness level. Nothing else
  ([PRIVACY.md](PRIVACY.md)).

## Why PostgreSQL

Several workers write ratings at the same time and we wanted real constraints: see
[ADR 0003](adr/0003-postgres.md).

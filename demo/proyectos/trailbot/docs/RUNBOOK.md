# Runbook

## The bot does not answer

1. Check the `trailbot` unit status and its last log lines.
2. If the unit is running, check the webhook info from the Bot API: Telegram reports the last error there.
3. If the last release is the suspect, roll back ([DEPLOY.md](DEPLOY.md)).

## Open-Meteo fails

`/today` falls back to ranking without weather and says so in the answer. If it fails for more than an hour, post a
note in the bot's channel. Most outages last minutes.

## A trail is wrong

Fix the row in `data/trails.csv` and deploy: the seed is an upsert, so the fix reaches the table on the next
release.

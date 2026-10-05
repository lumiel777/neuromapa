---
name: deploy
description: How trailbot is deployed: a small VPS, a systemd unit, releases side by side and a one-command rollback
metadata:
  node_type: memory
  type: reference
---

trailbot runs on a small VPS behind a reverse proxy. The service is the systemd unit in `deploy/trailbot.service`,
which runs uvicorn from `/opt/trailbot/current`.

- Each release goes to its own folder and `current` is a symlink; a rollback points it back and restarts the unit.
- The environment file with the bot token and the database password lives on the VPS only.
- The database is a managed PostgreSQL with daily backups.

Step by step, including the first install: `docs/DEPLOY.md`. When the bot stops answering: `docs/RUNBOOK.md`.

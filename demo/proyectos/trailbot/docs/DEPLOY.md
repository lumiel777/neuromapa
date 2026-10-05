# Deploy

## Layout on the VPS

- `/opt/trailbot/releases/<date>`: one folder per release.
- `/opt/trailbot/current`: symlink to the release that runs.
- The environment file with the bot token and the database URL lives in `/etc/trailbot/`, readable only by the
  service user.

## Releasing

1. Build the release folder and install the dependencies in the shared virtualenv.
2. Load the seed into `trail_routes`.
3. Point `current` to the new folder and restart the `trailbot` unit.
4. Send `/today` from the test account.

## Rolling back

Point `current` to the previous folder and restart the unit. Seed changes are upserts, so an older release still
works with a newer seed.

When the bot stops answering: [RUNBOOK.md](RUNBOOK.md).

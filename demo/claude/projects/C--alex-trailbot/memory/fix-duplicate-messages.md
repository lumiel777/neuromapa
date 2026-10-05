---
name: fix-duplicate-messages
description: Fix: Telegram retried slow webhook calls and /today answered twice; updates are now handled once by update_id
metadata:
  node_type: memory
  type: project
---

**What happened.** Sometimes `/today` answered twice, a few seconds apart.

**Why.** Telegram retries a webhook call that takes too long. Fetching several forecasts could take more than the
timeout, so the same update arrived again and was handled again.

**Fix.** `bot/main.py` remembers the `update_id` of every update it handled and answers a repeat with 200 without
doing anything. Forecasts are cached ([[weather-provider]]), so the first answer is also faster now.

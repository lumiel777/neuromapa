---
name: fix-timezone
description: Fix: after 9 pm the forecast was for the wrong day, because dates were computed in UTC
metadata:
  node_type: memory
  type: project
---

**What happened.** Users asking `/today` after 9 pm got tomorrow's forecast for today's hike.

**Why.** We asked Open-Meteo for daily values without a timezone, so days were split in UTC, three hours ahead of
Argentina.

**Fix.** Every forecast request sends the Córdoba timezone ([[weather-provider]]), and "today" is computed in that
timezone too. Tested by freezing the clock at 22:30 local time.

---
name: what-trailbot-does
description: What trailbot does: a Telegram bot that answers /today with a hike picked by weather, distance and fitness
metadata:
  node_type: memory
  type: project
---

trailbot answers one question: **where should I hike today?**

The user sets a home area and a fitness level from one to five. With `/today`, the bot looks at the trails within a
two-hour drive, gets the forecast for each one and returns the best three, with a line on why
([[trail-scoring]]). The other commands are in [[telegram-commands]].

The trails come from a hand-curated seed ([[trail-data]]) of the Sierras de Córdoba and Mendoza. The forecast comes
from Open-Meteo ([[weather-provider]]).

It is a side project with a few dozen users, mostly friends of friends. The launch plan is in
[[launch-checklist]].

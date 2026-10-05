---
name: weather
description: The forecast comes from Open-Meteo: no API key, daily values per trail, cached for thirty minutes
metadata:
  node_type: memory
  type: reference
---

We use the free Open-Meteo forecast API: no key, generous limits, and daily values that are enough for a hike.

- `weather.py:40` (`get_forecast`) asks for the daily maximum temperature, precipitation, maximum wind and weather
  code, in the Córdoba timezone.
- Results are cached per rounded coordinate for thirty minutes, so ten users near the same trail cost one call.
- A weather code of 95 or more means a storm, and the trail scores zero.

Why Open-Meteo and not a paid provider: `docs/adr/0002-open-meteo.md`. The timezone bug we had:
[[fix-timezone]].

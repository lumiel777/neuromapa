# ADR 0002: Open-Meteo for the forecast

**Status:** accepted (May 2025).

## Context

We need a daily forecast per trailhead: maximum temperature, rain, wind and storms. Paid providers need a key and a
card, and their free tiers are small.

## Decision

Use the Open-Meteo forecast API: free for non-commercial use, no key, daily values and a timezone parameter.

## Consequences

- Cache per rounded coordinate for 30 minutes to stay well under the limits.
- Always send the timezone, or days are split in UTC.
- If trailbot ever charges users, review the terms.

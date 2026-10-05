# Privacy

What trailbot stores, and nothing more:

| Data | Why | Kept until |
|---|---|---|
| Salted hash of the Telegram id | To recognise returning users | `/stop` |
| Home area (a city or a rounded point) | To find trails near home | `/stop` |
| Fitness level | For the scoring | `/stop` |
| Ratings | To improve suggestions | `/stop` |

We never store live locations, message texts or a history of which trails someone asked about. Logs have the
command name and the time, not the text.

`/stop` deletes all of the above at once. There is no soft delete and no backup older than seven days.

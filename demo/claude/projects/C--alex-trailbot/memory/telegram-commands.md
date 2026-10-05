---
name: telegram-commands
description: The Telegram commands trailbot answers (/today, /near, /rate, /stop, /help) and what each one does
metadata:
  node_type: memory
---

The bot answers **5 commands**, one handler each in `bot/handlers`:

- `/today`: the best three hikes for today ([[trail-scoring]]).
- `/near`: every trail within 40 km of home, no weather involved.
- `/rate <trail> <1-5>`: rate a trail you walked; once per trail per day ([[fix-rating-spam]]).
- `/stop`: forget me ([[privacy-rules]]).
- `/help`: the list above.

Anything else gets the help text. The user-facing wording is in `docs/COMMANDS.md`.

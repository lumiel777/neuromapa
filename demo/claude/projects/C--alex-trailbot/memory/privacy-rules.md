---
name: privacy-rules
description: Privacy rules for trailbot users: hashed Telegram ids, only a home area, and /stop deletes everything
metadata:
  node_type: memory
  type: feedback
---

- Users are stored by a salted hash of their Telegram id, never the raw id.
- We keep a **home area** the user chooses (a city or a rounded point), never their live location or a history of
  where they were.
- `/stop` deletes the user row, their ratings and their settings at once. No soft delete.
- Logs never contain message text.

**Why:** a hiking bot knows when someone is away from home. Alex decided early that the bot should not be able to
leak that.

**How to apply:** any new feature that wants location data needs a line in `docs/PRIVACY.md` first.

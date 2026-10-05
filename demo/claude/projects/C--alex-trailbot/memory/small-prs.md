---
name: small-prs
description: Keep pull requests small: one change, with its tests, and a description with what was wrong and why
metadata:
  node_type: memory
  type: feedback
---

Keep every pull request small: one change, with its tests, and a description that says what was wrong and why the
change fixes it. Run `pytest -q` and `ruff check .` before asking for review. Never mix a refactor with a behaviour
change in the same pull request.

**Why:** Alex reviews on the phone between other jobs; a small pull request can be read in five minutes.

**How to apply:** if a task needs a refactor first, open two pull requests.

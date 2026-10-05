---
name: fix-rating-spam
description: Fix: one user rated the same trail many times in a row; now one rating per user, per trail, per day
metadata:
  node_type: memory
  type: project
---

**What happened.** One user sent `/rate los-gigantes 1` forty times and pushed a good trail to the bottom.

**Why.** Nothing stopped repeated ratings.

**Fix.** A unique index on user hash, trail and day in `trail_ratings`; the handler answers "You already rated this
trail today". Averages now use the last rating of each user.

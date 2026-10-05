---
name: trail-scoring
description: How trails are ranked: difficulty weight times weather factor times distance factor, with a fitness rule
metadata:
  node_type: memory
  type: project
---

The score lives in `recommend.py:35` (`score_trail`):

- **Difficulty weight:** easy 1.0, moderate 0.8, hard 0.55. A hard trail for someone with fitness below three is
  multiplied by 0.4: we would rather suggest a nice moderate walk than send a beginner up Champaquí.
- **Weather factor:** zero with a storm or wind above 45 km/h; rain above one millimetre multiplies by 0.6; above
  32 degrees, by 0.7.
- **Distance factor:** full score up to 30 km from home, then it falls linearly, never below 0.2.

`rank_trails` drops anything that scored zero and breaks ties with the shorter trail. The long version, with the
reasons behind each number, is in `docs/SCORING.md`.

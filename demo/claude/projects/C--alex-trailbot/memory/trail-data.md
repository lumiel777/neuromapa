---
name: trail-data
description: The trail seed (data/trails.csv, curated by Alex), how it loads into trail_routes and what each column means
metadata:
  node_type: memory
  type: project
---

The trails are curated by hand in `data/trails.csv`: one row per trail with slug, name, difficulty, length in km,
the coordinates of the trailhead and the province. Today it covers the Sierras de Córdoba and the Mendoza
precordillera. The seed `data/trails.csv` has 13 lines: the header and 12 trails.

On deploy, the seed is loaded into the `trail_routes` table (upsert by slug), so fixing a trail is a one-line pull
request. Ratings go to `trail_ratings`, never back to the CSV.

Only trails Alex has walked go in. How to propose one: `docs/CONTRIBUTING.md`.

# Scoring

`score_trail` (`recommend.py:35`) multiplies three factors. A trail with score zero is never suggested.

## Difficulty weight

| Difficulty | Weight |
|---|---|
| easy | 1.0 |
| moderate | 0.8 |
| hard | 0.55 |

A hard trail for a user with fitness below three gets an extra 0.4. Early testers with fitness two were sent up
Champaquí on a sunny day; they did not enjoy it.

## Weather factor

- Storm (weather code 95 or more) or wind above 45 km/h: zero. Ridges in the Sierras are dangerous with strong wind.
- Rain above 1 mm: times 0.6. Wet granite is slippery, but a drizzle is fine in the valleys.
- Maximum above 32 °C: times 0.7. Most trails have no shade.

## Distance factor

Full score up to 30 km from home. After that it falls linearly and reaches the floor of 0.2 at 150 km. A great trail
far away can still beat a poor one next door.

## Ranking

`rank_trails` (`recommend.py:42`) sorts by score, breaks ties with the shorter trail and returns the top three.

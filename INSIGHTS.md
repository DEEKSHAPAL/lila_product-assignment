# LILA BLACK Dataset Insights

These insights were generated from the processed February 10-14, 2026 telemetry in `data_processed/all_events.parquet`.
Locations use an 8x8 grid over the 1024x1024 minimap, where A1 is the northwest corner and H8 is the southeast corner.

## Insight 1: GrandRift D5 is combat-heavy relative to traffic

### What caught my eye
Grid cell D5 (southwest of center) produces a noticeably larger share of kill events than its share of movement samples.

### Evidence
GrandRift D5 has 45 Kill/BotKill events, 23.3% of that map's 193 kill events. The same cell has 703 movement rows, 12.3% of 5,728 movement rows. That is a 1.9x kill concentration relative to traffic.

### Actionable recommendation
Review sightlines, cover, spawn approach routes, and loot pressure around D5. If this is intended, make the danger legible; if not, add alternate cover or route choices nearby.

### Metrics affected
Kill rate, time-to-first-death, route diversity, player retention after early deaths.

### Why a Level Designer should care
A cell that over-indexes on kills can become a forced fight location. That is valuable when intentional and frustrating when players feel pulled into it without readable choices.

## Insight 2: Storm deaths cluster around AmbroseValley D6

### What caught my eye
Storm deaths are not evenly distributed; the largest cluster lands in D6 (southwest of center).

### Evidence
AmbroseValley D6 contains 3 KilledByStorm events, 17.6% of AmbroseValley's 17 storm deaths and 7.7% of all 39 storm deaths in the dataset.

### Actionable recommendation
Check extraction paths, storm warning readability, and traversal friction near D6. Consider clearer escape affordances or intentional high-risk rewards if the cluster is desired.

### Metrics affected
Storm death rate, extraction success, late-match frustration, route completion.

### Why a Level Designer should care
Storm deaths are a direct signal that players failed to react, lacked a viable route, or accepted too much risk. A spatial cluster gives designers a concrete place to inspect.

## Insight 3: GrandRift C4 is loot-rich but under-contested

### What caught my eye
Grid cell C4 (northwest of center) attracts a meaningful share of loot pickups without a matching share of combat.

### Evidence
GrandRift C4 has 81 Loot events, 9.2% of that map's loot. It has only 5 Kill/Killed events, 2.1% of that map's combat, while still carrying 370 movement rows (6.5% of movement).

### Actionable recommendation
Treat C4 as a low-risk loot pocket candidate. Add patrol pressure, expose one approach, or intentionally keep it as a safer recovery route if the map needs a lower-tension option.

### Metrics affected
Loot pickup rate, combat around loot, risk/reward balance, route diversity.

### Why a Level Designer should care
Loot that is consistently collected without nearby combat can flatten extraction-shooter tension. Designers can either protect that role or tune the area to create a more deliberate choice.

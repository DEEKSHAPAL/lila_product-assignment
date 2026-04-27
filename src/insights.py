"""Evidence-backed dataset insights for level design review."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from string import ascii_uppercase

import pandas as pd

from src.config import IMAGE_SIZE
from src.utils import clean_number


GRID_SIZE = 8


@dataclass
class Insight:
    title: str
    caught_eye: str
    evidence: str
    recommendation: str
    metrics: str
    why_care: str


def _grid_frame(df: pd.DataFrame) -> pd.DataFrame:
    working = df[df["in_minimap_bounds"]].dropna(subset=["pixel_x", "pixel_y"]).copy()
    if working.empty:
        working["grid_zone"] = pd.Series(dtype="object")
        return working
    col = (working["pixel_x"] / IMAGE_SIZE * GRID_SIZE).astype(int).clip(0, GRID_SIZE - 1)
    row = (working["pixel_y"] / IMAGE_SIZE * GRID_SIZE).astype(int).clip(0, GRID_SIZE - 1)
    working["grid_col"] = col
    working["grid_row"] = row
    working["grid_zone"] = [f"{ascii_uppercase[c]}{r + 1}" for c, r in zip(col, row)]
    working["region"] = [zone_description(c, r) for c, r in zip(col, row)]
    return working


def zone_description(col: int, row: int) -> str:
    west_east = (
        "west" if col <= 1 else
        "west-central" if col <= 3 else
        "east-central" if col <= 5 else
        "east"
    )
    north_south = (
        "north" if row <= 1 else
        "north-central" if row <= 3 else
        "south-central" if row <= 5 else
        "south"
    )
    if west_east == "west-central" and north_south == "north-central":
        return "northwest of center"
    if west_east == "east-central" and north_south == "north-central":
        return "northeast of center"
    if west_east == "west-central" and north_south == "south-central":
        return "southwest of center"
    if west_east == "east-central" and north_south == "south-central":
        return "southeast of center"
    return f"{north_south} {west_east}"


def compute_event_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Return event counts by map and event group."""
    return (
        df.groupby(["map_id", "event_group"], dropna=False)
        .size()
        .reset_index(name="rows")
        .sort_values(["map_id", "rows"], ascending=[True, False])
    )


def compute_grid_hotspots(df: pd.DataFrame) -> pd.DataFrame:
    """Return 8x8 grid counts by map, zone, and event group."""
    working = _grid_frame(df)
    if working.empty:
        return pd.DataFrame()
    return (
        working.groupby(["map_id", "grid_zone", "region", "event_group"], dropna=False)
        .size()
        .reset_index(name="rows")
        .sort_values(["map_id", "event_group", "rows"], ascending=[True, True, False])
    )


def compute_early_combat(df: pd.DataFrame, seconds: int = 120) -> pd.DataFrame:
    """Return combat timing by map."""
    combat = df[df["event_group"].isin(["Kill", "Death"])]
    if combat.empty:
        return pd.DataFrame()
    rows = []
    for map_id, group in combat.groupby("map_id"):
        early = int(group["match_time_s"].le(seconds).sum())
        total = int(len(group))
        rows.append(
            {
                "map_id": map_id,
                "combat_events": total,
                "early_combat_events": early,
                "early_pct": early / total * 100 if total else 0,
            }
        )
    return pd.DataFrame(rows).sort_values("early_pct", ascending=False)


def compute_storm_clusters(df: pd.DataFrame) -> pd.DataFrame:
    """Return storm death grid clusters."""
    storm = _grid_frame(df[df["event_group"].eq("Storm")])
    if storm.empty:
        return pd.DataFrame()
    return (
        storm.groupby(["map_id", "grid_zone", "region"], dropna=False)
        .size()
        .reset_index(name="storm_deaths")
        .sort_values("storm_deaths", ascending=False)
    )


def compute_loot_combat_mismatch(df: pd.DataFrame) -> pd.DataFrame:
    """Return zones where loot share and combat share diverge."""
    grid = _grid_frame(df)
    if grid.empty:
        return pd.DataFrame()

    rows = []
    for map_id, group in grid.groupby("map_id"):
        zone = (
            group.groupby(["grid_zone", "region"])
            .agg(
                loot=("event_group", lambda values: int(values.eq("Loot").sum())),
                combat=("event_group", lambda values: int(values.isin(["Kill", "Death"]).sum())),
                movement=("event_group", lambda values: int(values.eq("Movement").sum())),
            )
            .reset_index()
        )
        total_loot = int(zone["loot"].sum())
        total_combat = int(zone["combat"].sum())
        total_movement = int(zone["movement"].sum())
        zone["map_id"] = map_id
        zone["loot_share"] = zone["loot"] / total_loot * 100 if total_loot else 0
        zone["combat_share"] = zone["combat"] / total_combat * 100 if total_combat else 0
        zone["traffic_share"] = zone["movement"] / total_movement * 100 if total_movement else 0
        zone["loot_minus_combat"] = zone["loot_share"] - zone["combat_share"]
        rows.append(zone)

    return pd.concat(rows, ignore_index=True).sort_values("loot_minus_combat", ascending=False)


def _share(count: int, total: int) -> float:
    return count / total * 100 if total else 0.0


def _build_combat_hotspot_insight(df: pd.DataFrame) -> Insight:
    grid = _grid_frame(df)
    movement = grid[grid["event_group"].eq("Movement")]
    kills = grid[grid["event_group"].eq("Kill")]

    movement_counts = movement.groupby(["map_id", "grid_zone", "region"]).size().rename("movement_rows")
    kill_counts = kills.groupby(["map_id", "grid_zone", "region"]).size().rename("kill_events")
    combined = pd.concat([movement_counts, kill_counts], axis=1).fillna(0).reset_index()

    map_totals = combined.groupby("map_id")[["movement_rows", "kill_events"]].sum().rename(
        columns={"movement_rows": "map_movement_rows", "kill_events": "map_kill_events"}
    )
    combined = combined.merge(map_totals, on="map_id", how="left")
    combined = combined[combined["kill_events"] > 0].copy()
    combined["kill_share"] = combined["kill_events"] / combined["map_kill_events"] * 100
    combined["traffic_share"] = combined["movement_rows"] / combined["map_movement_rows"] * 100
    combined["over_index"] = combined["kill_share"] - combined["traffic_share"]

    row = combined.sort_values(["over_index", "kill_events"], ascending=False).iloc[0]
    map_id = row["map_id"]
    zone = row["grid_zone"]
    region = row["region"]
    kill_count = int(row["kill_events"])
    total_kills = int(row["map_kill_events"])
    movement_count = int(row["movement_rows"])
    total_movement = int(row["map_movement_rows"])
    kill_share = _share(kill_count, total_kills)
    traffic_share = _share(movement_count, total_movement)
    ratio = kill_share / traffic_share if traffic_share else 0

    return Insight(
        title=f"{map_id} {zone} is combat-heavy relative to traffic",
        caught_eye=(
            f"Grid cell {zone} ({region}) produces a noticeably larger share of kill events "
            f"than its share of movement samples."
        ),
        evidence=(
            f"{map_id} {zone} has {kill_count:,} Kill/BotKill events, "
            f"{clean_number(kill_share)}% of that map's {total_kills:,} kill events. "
            f"The same cell has {movement_count:,} movement rows, "
            f"{clean_number(traffic_share)}% of {total_movement:,} movement rows. "
            f"That is a {clean_number(ratio)}x kill concentration relative to traffic."
        ),
        recommendation=(
            f"Review sightlines, cover, spawn approach routes, and loot pressure around {zone}. "
            "If this is intended, make the danger legible; if not, add alternate cover or route choices nearby."
        ),
        metrics="Kill rate, time-to-first-death, route diversity, player retention after early deaths.",
        why_care=(
            "A cell that over-indexes on kills can become a forced fight location. "
            "That is valuable when intentional and frustrating when players feel pulled into it without readable choices."
        ),
    )


def _build_storm_insight(df: pd.DataFrame) -> Insight:
    storm_clusters = compute_storm_clusters(df)
    if storm_clusters.empty:
        total_matches = df["match_id"].nunique()
        return Insight(
            title="Storm deaths are absent in this slice",
            caught_eye="No KilledByStorm events were present in the processed rows.",
            evidence=f"The dataset contains {len(df):,} rows across {total_matches:,} matches and 0 storm deaths.",
            recommendation="Confirm whether storm deaths were intentionally disabled or omitted from telemetry for this export.",
            metrics="Extraction pressure, storm readability, endgame survival rate.",
            why_care="Without storm death telemetry, designers cannot validate whether the one-directional storm is creating intended pressure.",
        )

    row = storm_clusters.iloc[0]
    map_id = row["map_id"]
    zone = row["grid_zone"]
    region = row["region"]
    count = int(row["storm_deaths"])
    map_storm = int(df[(df["map_id"].eq(map_id)) & (df["event_group"].eq("Storm"))].shape[0])
    all_storm = int(df["event_group"].eq("Storm").sum())
    map_pct = _share(count, map_storm)
    all_pct = _share(count, all_storm)

    return Insight(
        title=f"Storm deaths cluster around {map_id} {zone}",
        caught_eye=(
            f"Storm deaths are not evenly distributed; the largest cluster lands in {zone} ({region})."
        ),
        evidence=(
            f"{map_id} {zone} contains {count:,} KilledByStorm events, "
            f"{clean_number(map_pct)}% of {map_id}'s {map_storm:,} storm deaths and "
            f"{clean_number(all_pct)}% of all {all_storm:,} storm deaths in the dataset."
        ),
        recommendation=(
            f"Check extraction paths, storm warning readability, and traversal friction near {zone}. "
            "Consider clearer escape affordances or intentional high-risk rewards if the cluster is desired."
        ),
        metrics="Storm death rate, extraction success, late-match frustration, route completion.",
        why_care=(
            "Storm deaths are a direct signal that players failed to react, lacked a viable route, or accepted too much risk. "
            "A spatial cluster gives designers a concrete place to inspect."
        ),
    )


def _build_early_combat_insight(df: pd.DataFrame) -> Insight:
    early = compute_early_combat(df, seconds=120)
    if early.empty:
        return Insight(
            title="Combat timing needs more event data",
            caught_eye="No Kill or Death events were available for early-combat analysis.",
            evidence="The processed dataset has no rows in the Kill or Death event groups.",
            recommendation="Verify combat telemetry before using this export for pacing decisions.",
            metrics="Early combat rate, match pacing, first engagement timing.",
            why_care="Level Designers need combat timing to understand whether match openings support looting, scouting, or immediate fighting.",
        )

    row = early.iloc[0]
    map_id = row["map_id"]
    early_count = int(row["early_combat_events"])
    total = int(row["combat_events"])
    early_pct = float(row["early_pct"])
    median_times = (
        df[df["event_group"].isin(["Kill", "Death"])]
        .groupby("map_id")["match_time_s"]
        .median()
        .sort_values()
    )
    median = float(median_times.loc[map_id]) if map_id in median_times.index else 0.0

    return Insight(
        title=f"{map_id} front-loads combat in the first two minutes",
        caught_eye=(
            f"{map_id} has the highest share of Kill/Killed events before 02:00, "
            "which points to faster early engagements than the other maps."
        ),
        evidence=(
            f"{early_count:,} of {total:,} Kill/Killed events on {map_id} occur by 02:00 "
            f"({clean_number(early_pct)}%). The median combat event on this map happens at "
            f"{int(median // 60):02d}:{int(median % 60):02d}."
        ),
        recommendation=(
            "Review spawn spacing, first-loot distance, and bot patrol timing on this map. "
            "If early pressure is too high, spread high-value loot or soften direct spawn-to-spawn lanes."
        ),
        metrics="Time-to-first-combat, early death rate, loot-before-fight rate, match abandonment.",
        why_care=(
            "Opening pacing determines whether players feel they had agency before the first fight. "
            "A front-loaded map can be exciting, but it should be an intentional identity rather than an accidental spawn pattern."
        ),
    )


def _build_loot_combat_mismatch_insight(df: pd.DataFrame) -> Insight:
    mismatch = compute_loot_combat_mismatch(df)
    if mismatch.empty:
        return Insight(
            title="Loot and combat mismatch could not be computed",
            caught_eye="No in-bounds loot or combat zones were available for comparison.",
            evidence="The processed dataset did not contain enough in-bounds Loot, Kill, or Death rows to compare zone shares.",
            recommendation="Verify coordinate coverage before using this export for loot risk analysis.",
            metrics="Loot pickup rate, combat encounters near loot, route variety.",
            why_care="Loot placement should usually create a deliberate risk/reward shape, which requires comparing pickups against combat pressure.",
        )

    candidates = mismatch[mismatch["loot"].ge(20)].copy()
    if candidates.empty:
        candidates = mismatch.copy()
    row = candidates.sort_values(["loot_minus_combat", "loot"], ascending=False).iloc[0]
    map_id = row["map_id"]
    zone = row["grid_zone"]
    region = row["region"]
    loot = int(row["loot"])
    combat = int(row["combat"])
    movement = int(row["movement"])
    loot_share = float(row["loot_share"])
    combat_share = float(row["combat_share"])
    traffic_share = float(row["traffic_share"])

    return Insight(
        title=f"{map_id} {zone} is loot-rich but under-contested",
        caught_eye=(
            f"Grid cell {zone} ({region}) attracts a meaningful share of loot pickups without a matching share of combat."
        ),
        evidence=(
            f"{map_id} {zone} has {loot:,} Loot events, {clean_number(loot_share)}% of that map's loot. "
            f"It has only {combat:,} Kill/Killed events, {clean_number(combat_share)}% of that map's combat, "
            f"while still carrying {movement:,} movement rows ({clean_number(traffic_share)}% of movement)."
        ),
        recommendation=(
            f"Treat {zone} as a low-risk loot pocket candidate. Add patrol pressure, expose one approach, "
            "or intentionally keep it as a safer recovery route if the map needs a lower-tension option."
        ),
        metrics="Loot pickup rate, combat around loot, risk/reward balance, route diversity.",
        why_care=(
            "Loot that is consistently collected without nearby combat can flatten extraction-shooter tension. "
            "Designers can either protect that role or tune the area to create a more deliberate choice."
        ),
    )


def build_insight_markdown(df: pd.DataFrame) -> str:
    """Build exactly three practical insights from the processed data."""
    insights = [
        _build_combat_hotspot_insight(df),
        _build_storm_insight(df),
        _build_loot_combat_mismatch_insight(df),
    ]

    lines = [
        "# LILA BLACK Dataset Insights",
        "",
        "These insights were generated from the processed February 10-14, 2026 telemetry in `data_processed/all_events.parquet`.",
        "Locations use an 8x8 grid over the 1024x1024 minimap, where A1 is the northwest corner and H8 is the southeast corner.",
        "",
    ]
    for index, insight in enumerate(insights, start=1):
        lines.extend(
            [
                f"## Insight {index}: {insight.title}",
                "",
                "### What caught my eye",
                insight.caught_eye,
                "",
                "### Evidence",
                insight.evidence,
                "",
                "### Actionable recommendation",
                insight.recommendation,
                "",
                "### Metrics affected",
                insight.metrics,
                "",
                "### Why a Level Designer should care",
                insight.why_care,
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def save_insights_markdown(df: pd.DataFrame, output_path: Path) -> str:
    """Write INSIGHTS.md and return the generated markdown."""
    markdown = build_insight_markdown(df)
    output_path.write_text(markdown, encoding="utf-8")
    return markdown

"""Raw telemetry normalization and summary creation."""

from __future__ import annotations

import pandas as pd

from src.config import EVENT_CATEGORIES, EVENT_DISPLAY, EVENT_GROUPS, KNOWN_EVENTS, MOVEMENT_EVENTS
from src.coordinate_mapping import add_minimap_coordinates
from src.utils import format_match_time, safe_numeric_check, short_id


def decode_event_value(value: object) -> str:
    """Decode event bytes safely into clean strings."""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace").strip()
    if isinstance(value, bytearray):
        return bytes(value).decode("utf-8", errors="replace").strip()
    if value is None or pd.isna(value):
        return "Unknown"
    text = str(value).strip()
    if text.startswith("b'") and text.endswith("'"):
        text = text[2:-1]
    if text.startswith('b"') and text.endswith('"'):
        text = text[2:-1]
    return text.strip()


def classify_player(user_id: object) -> str:
    """Classify a user id as Human or Bot."""
    return "Bot" if safe_numeric_check(user_id) else "Human"


def classify_event_group(event: object) -> str:
    """Group raw event names for filters and markers."""
    return EVENT_GROUPS.get(str(event), "Other")


def classify_event_category(event: object) -> str:
    """Group raw event names into broad UX categories."""
    return EVENT_CATEGORIES.get(str(event), "Other")


def _timestamp_to_ms(series: pd.Series) -> pd.Series:
    dt = pd.to_datetime(series, errors="coerce")
    ts_ms = pd.Series(pd.NA, index=series.index, dtype="Float64")
    valid = dt.notna()
    if valid.any():
        # Parquet timestamp[ms] can remain millisecond-backed in newer Pandas.
        # Force the unit to ms before reading integer epoch values.
        ts_ms.loc[valid] = dt.loc[valid].astype("datetime64[ms]").astype("int64").astype("float64")
    return ts_ms


def normalize_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    """Convert raw timestamp values into elapsed match seconds."""
    result = df.copy()
    result["ts_raw"] = result["ts"].astype(str)
    result["ts_ms"] = _timestamp_to_ms(result["ts"])

    match_start = result.groupby("match_id", dropna=False)["ts_ms"].transform("min")
    result["match_time_s"] = ((result["ts_ms"] - match_start) / 1000).astype("float64")
    result.loc[result["match_time_s"].isna(), "match_time_s"] = 0.0
    result.loc[result["match_time_s"] < 0, "match_time_s"] = 0.0
    result["match_time_label"] = result["match_time_s"].map(format_match_time)
    return result


def preprocess_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize raw rows into the app-ready event model."""
    if df.empty:
        return df.copy()

    result = df.copy()
    required = ["user_id", "match_id", "map_id", "x", "y", "z", "ts", "event"]
    missing = [column for column in required if column not in result.columns]
    if missing:
        raise ValueError(f"Raw data is missing required columns: {missing}")

    result["user_id"] = result["user_id"].astype(str)
    result["match_id"] = result["match_id"].astype(str)
    result["map_id"] = result["map_id"].astype(str)
    result["event"] = result["event"].map(decode_event_value)
    result["unknown_event"] = ~result["event"].isin(KNOWN_EVENTS)

    result["is_bot"] = result["user_id"].map(safe_numeric_check)
    result["player_type"] = result["user_id"].map(classify_player)
    result["event_group"] = result["event"].map(classify_event_group)
    result["event_category"] = result["event"].map(classify_event_category)
    result["event_display"] = result["event"].map(lambda value: EVENT_DISPLAY.get(value, value))
    result["is_movement"] = result["event"].isin(MOVEMENT_EVENTS)

    result["user_id_short"] = result["user_id"].map(short_id)
    result["match_id_short"] = result["match_id"].map(short_id)

    result = normalize_timestamps(result)
    result = add_minimap_coordinates(result)

    sort_columns = ["map_id", "match_id", "user_id", "match_time_s"]
    result = result.sort_values(sort_columns, kind="mergesort").reset_index(drop=True)
    return result


def _count_group(group: pd.DataFrame, event_group: str) -> int:
    return int(group["event_group"].eq(event_group).sum())


def create_match_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Create one row per map/date/match for filters and match summary views."""
    rows: list[dict[str, object]] = []
    if df.empty:
        return pd.DataFrame(rows)

    group_columns = ["map_id", "source_date", "match_id"]
    for (map_id, source_date, match_id), group in df.groupby(group_columns, dropna=False):
        human_players = group.loc[group["player_type"].eq("Human"), "user_id"].nunique()
        bot_players = group.loc[group["player_type"].eq("Bot"), "user_id"].nunique()
        rows.append(
            {
                "map_id": map_id,
                "source_date": source_date,
                "match_id": match_id,
                "match_id_short": short_id(match_id),
                "total_events": int(len(group)),
                "movement_rows": int(group["is_movement"].sum()),
                "players": int(group["user_id"].nunique()),
                "human_players": int(human_players),
                "bot_players": int(bot_players),
                "kills": _count_group(group, "Kill"),
                "deaths": _count_group(group, "Death"),
                "storm_deaths": _count_group(group, "Storm"),
                "loot_events": _count_group(group, "Loot"),
                "duration_s": float(group["match_time_s"].max()),
                "duration_label": format_match_time(group["match_time_s"].max()),
                "first_event_s": float(group["match_time_s"].min()),
                "last_event_s": float(group["match_time_s"].max()),
            }
        )
    return pd.DataFrame(rows).sort_values(["map_id", "source_date", "match_id"]).reset_index(drop=True)


def create_player_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Create one row per player journey."""
    rows: list[dict[str, object]] = []
    if df.empty:
        return pd.DataFrame(rows)

    group_columns = ["map_id", "source_date", "match_id", "user_id", "player_type"]
    for (map_id, source_date, match_id, user_id, player_type), group in df.groupby(group_columns, dropna=False):
        rows.append(
            {
                "map_id": map_id,
                "source_date": source_date,
                "match_id": match_id,
                "user_id": user_id,
                "user_id_short": short_id(user_id),
                "player_type": player_type,
                "events": int(len(group)),
                "movement_rows": int(group["is_movement"].sum()),
                "kills": _count_group(group, "Kill"),
                "deaths": _count_group(group, "Death"),
                "storm_deaths": _count_group(group, "Storm"),
                "loot_events": _count_group(group, "Loot"),
                "duration_s": float(group["match_time_s"].max()),
                "start_x": float(group["x"].iloc[0]) if group["x"].notna().any() else None,
                "start_z": float(group["z"].iloc[0]) if group["z"].notna().any() else None,
                "in_bounds_rows": int(group["in_minimap_bounds"].sum()),
            }
        )
    return pd.DataFrame(rows).sort_values(["map_id", "source_date", "match_id", "player_type", "user_id"]).reset_index(drop=True)

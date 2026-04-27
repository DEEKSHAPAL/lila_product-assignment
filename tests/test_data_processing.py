from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.preprocessing import (
    classify_event_group,
    classify_player,
    decode_event_value,
    preprocess_dataframe,
)


def test_decode_event_value_handles_bytes_and_strings() -> None:
    assert decode_event_value(b"Position") == "Position"
    assert decode_event_value(b"KilledByStorm") == "KilledByStorm"
    assert decode_event_value(bytearray(b"BotKilled")) == "BotKilled"
    assert decode_event_value("Loot") == "Loot"


def test_bot_detection_uses_numeric_user_id() -> None:
    assert classify_player("1440") == "Bot"
    assert classify_player("382") == "Bot"
    assert classify_player("f4e072fa-b7af-4761-b567-1d95b7ad0108") == "Human"


def test_event_grouping() -> None:
    assert classify_event_group("Position") == "Movement"
    assert classify_event_group("BotPosition") == "Movement"
    assert classify_event_group("Kill") == "Kill"
    assert classify_event_group("BotKill") == "Kill"
    assert classify_event_group("Killed") == "Death"
    assert classify_event_group("BotKilled") == "Death"
    assert classify_event_group("KilledByStorm") == "Storm"
    assert classify_event_group("Loot") == "Loot"
    assert classify_event_group("SomethingElse") == "Other"


def test_preprocess_dataframe_normalizes_match_time_and_columns() -> None:
    raw = pd.DataFrame(
        {
            "user_id": ["player-1", "1440", "player-1"],
            "match_id": ["match-a.nakama-0", "match-a.nakama-0", "match-a.nakama-0"],
            "map_id": ["AmbroseValley", "AmbroseValley", "AmbroseValley"],
            "x": [-301.45, -280.85, -250.0],
            "y": [124.0, 121.0, 125.0],
            "z": [-355.55, -323.35, -300.0],
            "ts": pd.to_datetime(
                [
                    "1970-01-01 00:00:10.000",
                    "1970-01-01 00:00:15.000",
                    "1970-01-01 00:00:40.000",
                ]
            ),
            "event": [b"Position", b"BotPosition", b"Kill"],
            "source_file": ["a", "b", "a"],
            "source_path": ["February_10/a", "February_10/b", "February_10/a"],
            "source_date": ["February_10", "February_10", "February_10"],
        }
    )

    processed = preprocess_dataframe(raw)

    assert set(
        [
            "event_group",
            "event_category",
            "event_display",
            "is_bot",
            "player_type",
            "match_time_s",
            "pixel_x",
            "pixel_y",
            "in_minimap_bounds",
        ]
    ).issubset(processed.columns)
    assert set(processed["event"].tolist()) == {"Position", "Kill", "BotPosition"}
    assert processed["match_time_s"].min() == 0
    assert processed["match_time_s"].max() == 30
    assert processed.loc[processed["user_id"].eq("1440"), "player_type"].iloc[0] == "Bot"
    assert processed["unknown_event"].sum() == 0


def test_processed_data_contains_required_columns_if_prepared() -> None:
    processed_path = Path(__file__).resolve().parents[1] / "data_processed" / "all_events.parquet"
    if not processed_path.exists():
        pytest.skip("Processed data has not been generated yet.")

    processed = pd.read_parquet(processed_path)
    required_columns = {
        "user_id",
        "match_id",
        "map_id",
        "x",
        "y",
        "z",
        "ts",
        "event",
        "source_date",
        "source_file",
        "is_bot",
        "player_type",
        "event_group",
        "pixel_x",
        "pixel_y",
        "in_minimap_bounds",
        "match_time_s",
        "match_time_label",
    }

    assert required_columns.issubset(processed.columns)
    assert processed["event"].map(lambda value: not str(value).startswith("b'")).all()

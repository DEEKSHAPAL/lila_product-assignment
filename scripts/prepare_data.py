from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.coordinate_mapping import validate_coordinate_mapping  # noqa: E402
from src.data_loader import load_all_raw_data, save_processed_data  # noqa: E402
from src.preprocessing import create_match_summary, create_player_summary, preprocess_dataframe  # noqa: E402


def main() -> None:
    print("Preparing LILA BLACK telemetry...")
    raw_df, report = load_all_raw_data(ROOT, verbose=True)
    if raw_df.empty:
        raise SystemExit("No raw rows loaded. Confirm February_* folders are present.")

    processed = preprocess_dataframe(raw_df)
    match_summary = create_match_summary(processed)
    player_summary = create_player_summary(processed)

    validation = validate_coordinate_mapping()
    if not validation["within_tolerance"]:
        raise SystemExit(f"Coordinate validation failed: {validation}")

    report.update(
        {
            "rows_processed": int(len(processed)),
            "maps": sorted(processed["map_id"].dropna().unique().tolist()),
            "matches": int(processed["match_id"].nunique()),
            "players": int(processed["user_id"].nunique()),
            "unknown_events": int(processed["unknown_event"].sum()),
            "out_of_bounds_rows": int((~processed["in_minimap_bounds"]).sum()),
            "coordinate_validation": validation,
        }
    )
    save_processed_data(processed, ROOT, report)

    print()
    print("Processed outputs written to data_processed/")
    print(f"- all_events.parquet: {len(processed):,} rows")
    print(f"- match_summary.parquet: {len(match_summary):,} map/date/match rows")
    print(f"- player_summary.parquet: {len(player_summary):,} journeys")
    print(f"Maps: {', '.join(report['maps'])}")
    print(f"Unknown events: {report['unknown_events']:,}")
    print(
        "Ambrose sample maps to "
        f"({validation['pixel_x']:.1f}, {validation['pixel_y']:.1f}) "
        "with expected near (78, 890)."
    )


if __name__ == "__main__":
    main()

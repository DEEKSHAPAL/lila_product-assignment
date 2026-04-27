from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.data_loader import load_all_raw_data, load_processed_data, save_processed_data  # noqa: E402
from src.insights import (  # noqa: E402
    compute_early_combat,
    compute_event_summary,
    compute_grid_hotspots,
    compute_loot_combat_mismatch,
    compute_storm_clusters,
    save_insights_markdown,
)
from src.preprocessing import preprocess_dataframe  # noqa: E402


def ensure_processed():
    try:
        return load_processed_data(ROOT)
    except FileNotFoundError:
        raw_df, report = load_all_raw_data(ROOT, verbose=True)
        processed = preprocess_dataframe(raw_df)
        save_processed_data(processed, ROOT, report)
        return load_processed_data(ROOT)


def main() -> None:
    events, _, _, _ = ensure_processed()
    output_path = ROOT / "INSIGHTS.md"
    markdown = save_insights_markdown(events, output_path)

    print("Generated INSIGHTS.md")
    print()
    print("Event counts by map/event group:")
    print(compute_event_summary(events).to_string(index=False))
    print()
    print("Top grid hotspots:")
    hotspots = compute_grid_hotspots(events)
    print(hotspots.head(20).to_string(index=False))
    print()
    print("Storm clusters:")
    storm = compute_storm_clusters(events)
    print(storm.head(10).to_string(index=False) if not storm.empty else "No storm deaths found.")
    print()
    print("Early combat by map:")
    early = compute_early_combat(events)
    print(early.to_string(index=False) if not early.empty else "No combat events found.")
    print()
    print("Loot vs combat mismatch:")
    mismatch = compute_loot_combat_mismatch(events)
    print(mismatch.head(10).to_string(index=False) if not mismatch.empty else "No mismatch rows found.")
    print()
    print(markdown)


if __name__ == "__main__":
    main()

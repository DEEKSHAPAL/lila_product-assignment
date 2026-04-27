from __future__ import annotations

import sys
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import DATA_FOLDERS, MAP_CONFIG  # noqa: E402
from src.data_loader import find_raw_files, load_all_raw_data  # noqa: E402
from src.preprocessing import decode_event_value  # noqa: E402


def main() -> None:
    print("LILA BLACK raw data inspection")
    print(f"Project root: {ROOT}")
    print()

    total_files = 0
    for folder_name in DATA_FOLDERS:
        folder = ROOT / folder_name
        files = [path for path in folder.iterdir() if path.is_file() and not path.name.startswith(".")] if folder.exists() else []
        total_files += len(files)
        size = sum(path.stat().st_size for path in files)
        print(f"{folder_name}: {len(files):,} files, {size / 1024 / 1024:.2f} MB")
    print(f"Total raw files: {total_files:,}")
    print()

    print("Minimaps:")
    for map_id, cfg in MAP_CONFIG.items():
        path = ROOT / "minimaps" / cfg["image"]
        print(f"- {map_id}: {path.name} ({'found' if path.exists() else 'missing'})")
    print()

    raw_files = find_raw_files(ROOT)
    if not raw_files:
        raise SystemExit("No raw files found.")

    sample = raw_files[0]
    table = pq.read_table(sample)
    print(f"Sample file: {sample.relative_to(ROOT)}")
    print(table.schema)
    print()

    raw_df, report = load_all_raw_data(ROOT, verbose=True)
    if raw_df.empty:
        raise SystemExit("No rows were readable.")

    raw_df["event_decoded"] = raw_df["event"].map(decode_event_value)
    print("Load report:")
    print(report)
    print()

    print("Event values:")
    print(raw_df["event_decoded"].value_counts().to_string())
    print()

    print("Maps:")
    print(raw_df["map_id"].value_counts().to_string())
    print()

    print("Coordinate ranges by map:")
    ranges = raw_df.groupby("map_id")[["x", "z"]].agg(["min", "max"])
    print(ranges.to_string())
    print()

    print(f"Unique matches: {raw_df['match_id'].nunique():,}")
    print(f"Unique players/bots: {raw_df['user_id'].nunique():,}")


if __name__ == "__main__":
    main()


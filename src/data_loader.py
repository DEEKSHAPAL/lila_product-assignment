"""Raw and processed data loading helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow.parquet as pq

from src.config import DATA_FOLDERS, PROCESSED_DIR
from src.preprocessing import create_match_summary, create_player_summary
from src.utils import ensure_directory


def processed_dir(root: Path) -> Path:
    return root / PROCESSED_DIR


def find_raw_files(root: Path) -> list[Path]:
    """Find all source journey files in the February_* folders."""
    files: list[Path] = []
    for folder_name in DATA_FOLDERS:
        folder = root / folder_name
        if not folder.exists():
            continue
        files.extend(path for path in folder.iterdir() if path.is_file() and not path.name.startswith("."))
    return sorted(files)


def read_single_file(path: Path) -> pd.DataFrame:
    """Read one extensionless parquet journey file and attach source metadata."""
    table = pq.read_table(path)
    df = table.to_pandas()
    df["source_file"] = path.name
    df["source_path"] = str(path.relative_to(path.parents[1]))
    df["source_date"] = path.parent.name
    return df


def load_all_raw_data(root: Path, verbose: bool = True) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Load every readable parquet file and return a dataframe plus report."""
    raw_files = find_raw_files(root)
    frames: list[pd.DataFrame] = []
    failed: list[dict[str, str]] = []

    for index, path in enumerate(raw_files, start=1):
        try:
            frames.append(read_single_file(path))
        except Exception as exc:  # noqa: BLE001 - report and keep loading the remaining files.
            failed.append({"path": str(path), "error": str(exc)})
        if verbose and index % 250 == 0:
            print(f"Read {index:,}/{len(raw_files):,} files...")

    if frames:
        df = pd.concat(frames, ignore_index=True)
    else:
        df = pd.DataFrame()

    report = {
        "raw_files_found": len(raw_files),
        "loaded_files": len(frames),
        "failed_files": len(failed),
        "failures": failed,
        "rows_loaded": int(len(df)),
    }
    if verbose:
        print(
            f"Loaded {report['loaded_files']:,}/{report['raw_files_found']:,} files, "
            f"{report['rows_loaded']:,} rows, {report['failed_files']:,} failures."
        )
    return df, report


def save_processed_data(df: pd.DataFrame, root: Path, report: dict[str, Any] | None = None) -> None:
    """Save app-ready events and summary parquet files."""
    output_dir = ensure_directory(processed_dir(root))
    df.to_parquet(output_dir / "all_events.parquet", index=False)
    create_match_summary(df).to_parquet(output_dir / "match_summary.parquet", index=False)
    create_player_summary(df).to_parquet(output_dir / "player_summary.parquet", index=False)
    if report is not None:
        (output_dir / "processing_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


def load_processed_data(root: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Load processed event and summary tables."""
    output_dir = processed_dir(root)
    events_path = output_dir / "all_events.parquet"
    match_path = output_dir / "match_summary.parquet"
    player_path = output_dir / "player_summary.parquet"

    if not events_path.exists():
        raise FileNotFoundError(f"Processed data not found: {events_path}")

    events = pd.read_parquet(events_path)
    match_summary = pd.read_parquet(match_path) if match_path.exists() else create_match_summary(events)
    player_summary = pd.read_parquet(player_path) if player_path.exists() else create_player_summary(events)

    report_path = output_dir / "processing_report.json"
    report: dict[str, Any] = {}
    if report_path.exists():
        report = json.loads(report_path.read_text(encoding="utf-8"))
    return events, match_summary, player_summary, report


from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image

from src.config import HEATMAP_EVENT_GROUPS, MAP_CONFIG
from src.data_loader import load_all_raw_data, load_processed_data, save_processed_data
from src.coordinate_mapping import validate_coordinate_mapping
from src.preprocessing import preprocess_dataframe
from src.utils import date_sort_key, format_match_time, short_id
from src.visualization import create_map_figure


ROOT = Path(__file__).parent
ALL_DATES = "All dates"
ALL_MATCHES = "All matches"


st.set_page_config(
    page_title="LILA BLACK Player Journey Visualizer",
    page_icon="LB",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_css() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background: #0e1117;
            color: #f2f4f8;
        }
        [data-testid="stSidebar"] {
            background: #141923;
            border-right: 1px solid rgba(255,255,255,0.08);
        }
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
        }
        h1, h2, h3 {
            letter-spacing: 0;
        }
        .metric-card {
            background: #171d29;
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 8px;
            padding: 0.85rem 0.9rem;
            min-height: 96px;
        }
        .metric-label {
            color: #9ba8bd;
            font-size: 0.76rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }
        .metric-value {
            color: #f8fafc;
            font-size: 1.5rem;
            font-weight: 700;
            margin-top: 0.2rem;
        }
        .metric-note {
            color: #7f8ca3;
            font-size: 0.76rem;
            margin-top: 0.15rem;
        }
        .small-note {
            color: #9ba8bd;
            font-size: 0.85rem;
        }
        div[data-testid="stDataFrame"] {
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 8px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner="Loading and preparing telemetry...")
def load_or_prepare_data(root_text: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    root = Path(root_text)
    try:
        return load_processed_data(root)
    except FileNotFoundError:
        raw_df, report = load_all_raw_data(root, verbose=False)
        processed = preprocess_dataframe(raw_df)
        report.update(
            {
                "rows_processed": int(len(processed)),
                "maps": sorted(processed["map_id"].dropna().unique().tolist()),
                "matches": int(processed["match_id"].nunique()),
                "players": int(processed["user_id"].nunique()),
                "unknown_events": int(processed["unknown_event"].sum()),
                "out_of_bounds_rows": int((~processed["in_minimap_bounds"]).sum()),
                "coordinate_validation": validate_coordinate_mapping(),
            }
        )
        save_processed_data(processed, root, report)
        return load_processed_data(root)


def apply_player_visibility(df: pd.DataFrame, show_humans: bool, show_bots: bool) -> pd.DataFrame:
    if show_humans and show_bots:
        return df
    if show_humans:
        return df[df["player_type"].eq("Human")]
    if show_bots:
        return df[df["player_type"].eq("Bot")]
    return df.iloc[0:0]


def render_metric_card(label: str, value: object, note: str = "") -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_counts(df: pd.DataFrame) -> dict[str, int]:
    return {
        "rows": int(len(df)),
        "players": int(df["user_id"].nunique()) if not df.empty else 0,
        "humans": int(df.loc[df["player_type"].eq("Human"), "user_id"].nunique()) if not df.empty else 0,
        "bots": int(df.loc[df["player_type"].eq("Bot"), "user_id"].nunique()) if not df.empty else 0,
        "kills": int(df["event_group"].eq("Kill").sum()) if not df.empty else 0,
        "deaths": int(df["event_group"].eq("Death").sum()) if not df.empty else 0,
        "storm_deaths": int(df["event_group"].eq("Storm").sum()) if not df.empty else 0,
        "loot": int(df["event_group"].eq("Loot").sum()) if not df.empty else 0,
        "movement": int(df["is_movement"].sum()) if not df.empty else 0,
    }


def format_match_option(match_id: str, summary: pd.DataFrame) -> str:
    if match_id == ALL_MATCHES:
        return ALL_MATCHES
    row = summary[summary["match_id"].eq(match_id)]
    if row.empty:
        return match_id
    item = row.iloc[0]
    return (
        f"{short_id(match_id, 8)} | {item['duration_label']} | "
        f"{int(item['players'])} players | {int(item['total_events']):,} rows"
    )


def make_event_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    table = df.copy()
    table["event_priority"] = np.where(table["is_movement"], 1, 0)
    table = table.sort_values(["event_priority", "match_time_s", "event"])
    columns = [
        "match_time_label",
        "event",
        "event_group",
        "user_id_short",
        "player_type",
        "x",
        "z",
        "map_id",
        "source_date",
        "match_id",
    ]
    table = table[columns].rename(
        columns={
            "match_time_label": "time",
            "user_id_short": "user_id",
            "map_id": "map",
            "source_date": "date",
        }
    )
    return table


def minimap_status(root: Path) -> pd.DataFrame:
    rows = []
    for map_id, cfg in MAP_CONFIG.items():
        path = root / "minimaps" / cfg["image"]
        exists = path.exists()
        width = height = None
        if exists:
            with Image.open(path) as image:
                width, height = image.size
        rows.append(
            {
                "map": map_id,
                "file": cfg["image"],
                "exists": exists,
                "width": width,
                "height": height,
                "expected": "1024x1024",
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    inject_css()

    st.title("LILA BLACK Player Journey Visualizer")
    st.caption(
        "Explore player routes, combat hotspots, loot behavior, storm deaths, and bot/human movement across production matches."
    )

    try:
        events, match_summary, player_summary, report = load_or_prepare_data(str(ROOT))
    except Exception as exc:  # noqa: BLE001 - Streamlit should fail with a useful message.
        st.error("The telemetry could not be loaded or processed.")
        st.exception(exc)
        st.stop()

    if events.empty:
        st.warning("No telemetry rows were loaded. Check that the February_* folders are present.")
        st.stop()

    with st.sidebar:
        st.header("Filters")
        available_maps = [map_id for map_id in MAP_CONFIG if map_id in set(events["map_id"].unique())]
        selected_map = st.selectbox("Map", available_maps, index=0)

        map_df = events[events["map_id"].eq(selected_map)]
        date_values = sorted(map_df["source_date"].dropna().unique().tolist(), key=date_sort_key)
        selected_date = st.selectbox("Date", [ALL_DATES] + date_values, index=0)

        date_df = map_df if selected_date == ALL_DATES else map_df[map_df["source_date"].eq(selected_date)]
        scoped_summary = match_summary[
            match_summary["map_id"].eq(selected_map)
            & (match_summary["source_date"].eq(selected_date) if selected_date != ALL_DATES else True)
        ].sort_values(["source_date", "duration_s", "match_id"], ascending=[True, False, True])

        match_ids = scoped_summary["match_id"].dropna().unique().tolist()
        selected_match = st.selectbox(
            "Match",
            [ALL_MATCHES] + match_ids,
            index=0,
            format_func=lambda value: format_match_option(value, scoped_summary),
        )
        if selected_match != ALL_MATCHES:
            st.caption(f"Full match id: {selected_match}")

        st.divider()
        st.subheader("Player visibility")
        show_humans = st.checkbox("Show humans", value=True)
        show_bots = st.checkbox("Show bots", value=True)

        st.subheader("Events")
        show_kills = st.checkbox("Show kills", value=True)
        show_deaths = st.checkbox("Show deaths", value=True)
        show_loot = st.checkbox("Show loot", value=True)
        show_storm = st.checkbox("Show storm deaths", value=True)

        enabled_groups = []
        if show_kills:
            enabled_groups.append("Kill")
        if show_deaths:
            enabled_groups.append("Death")
        if show_loot:
            enabled_groups.append("Loot")
        if show_storm:
            enabled_groups.append("Storm")

        st.subheader("Heatmap")
        heatmap_mode = st.radio(
            "Overlay",
            list(HEATMAP_EVENT_GROUPS.keys()),
            index=0,
            help="Heatmap intensity is the count of rows in each minimap grid bin.",
        )

    selected_df = date_df if selected_match == ALL_MATCHES else date_df[date_df["match_id"].eq(selected_match)]

    if selected_df.empty:
        st.warning("No rows match the selected map/date/match filters.")
        st.stop()

    single_match = selected_match != ALL_MATCHES
    current_time = float(selected_df["match_time_s"].max())
    show_full_match_path = True
    window_label = "Full elapsed path"

    with st.sidebar:
        if single_match:
            st.divider()
            st.subheader("Timeline")
            duration = float(selected_df["match_time_s"].max())
            if duration <= 10:
                max_seconds = max(0.01, float(np.ceil(duration * 100) / 100))
                current_time = float(st.slider("Match time", 0.0, max_seconds, max_seconds, step=0.01))
            else:
                max_seconds = max(1, int(np.ceil(duration)))
                current_time = float(st.slider("Match time", 0, max_seconds, max_seconds))
            st.caption(f"Current time: {format_match_time(current_time)} / {format_match_time(duration)}")
            show_full_match_path = st.checkbox("Show full match path", value=True)
            window_label = st.selectbox(
                "Recent time window",
                ["Full elapsed path", "Last 30 seconds", "Last 60 seconds", "Last 120 seconds"],
                index=0,
            )
        else:
            st.divider()
            st.caption("Select a single match to enable timeline playback controls.")

    if single_match:
        up_to_time = selected_df[selected_df["match_time_s"].le(current_time)]
        if window_label == "Full elapsed path":
            marker_heat_df = up_to_time
        else:
            seconds = int(window_label.split()[1])
            start_time = max(0, current_time - seconds)
            marker_heat_df = up_to_time[up_to_time["match_time_s"].ge(start_time)]
        path_df = selected_df if show_full_match_path else marker_heat_df
        draw_paths = True
        metric_df = apply_player_visibility(up_to_time, show_humans, show_bots)
        table_source_df = apply_player_visibility(marker_heat_df, show_humans, show_bots)
    else:
        path_df = selected_df.iloc[0:0]
        marker_heat_df = selected_df
        draw_paths = False
        metric_df = apply_player_visibility(selected_df, show_humans, show_bots)
        table_source_df = metric_df

    visible_path_df = apply_player_visibility(path_df, show_humans, show_bots)
    visible_marker_heat_df = apply_player_visibility(marker_heat_df, show_humans, show_bots)

    counts = metric_counts(metric_df)
    c1, c2, c3, c4, c5, c6, c7, c8 = st.columns(8)
    with c1:
        render_metric_card("Total rows", f"{counts['rows']:,}", f"{counts['movement']:,} movement")
    with c2:
        render_metric_card("Players", f"{counts['players']:,}", "visible unique ids")
    with c3:
        render_metric_card("Humans", f"{counts['humans']:,}", "UUID user ids")
    with c4:
        render_metric_card("Bots", f"{counts['bots']:,}", "numeric user ids")
    with c5:
        render_metric_card("Kills", f"{counts['kills']:,}", "Kill + BotKill")
    with c6:
        render_metric_card("Deaths", f"{counts['deaths']:,}", "Killed + BotKilled")
    with c7:
        render_metric_card("Storm deaths", f"{counts['storm_deaths']:,}", "KilledByStorm")
    with c8:
        render_metric_card("Loot", f"{counts['loot']:,}", "Loot pickups")

    map_tab, table_tab, summary_tab, quality_tab = st.tabs(
        ["Map View", "Event Table", "Match Summary", "Data Quality"]
    )

    with map_tab:
        if not show_humans and not show_bots:
            st.warning("Both player visibility toggles are off. Enable humans or bots to show telemetry.")
        else:
            if not single_match:
                st.info("Aggregate view suppresses individual paths by default. Use heatmaps and event markers, or select a match for paths.")
            if heatmap_mode != "None":
                st.caption(f"{heatmap_mode} heatmap intensity is a row count per pixel bin; brighter areas have more matching telemetry.")
            try:
                fig, render_stats = create_map_figure(
                    df=visible_marker_heat_df,
                    map_id=selected_map,
                    project_root=ROOT,
                    heatmap_mode=heatmap_mode,
                    show_humans=show_humans,
                    show_bots=show_bots,
                    enabled_event_groups=enabled_groups,
                    draw_paths=draw_paths,
                    path_df=visible_path_df,
                    marker_df=visible_marker_heat_df,
                    heatmap_df=visible_marker_heat_df,
                )
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": True})
                if single_match and render_stats["path_traces"] == 0:
                    st.caption("This match has no drawable movement path for the current visibility/time filters.")
            except Exception as exc:  # noqa: BLE001
                st.error("The map visualization could not be rendered.")
                st.exception(exc)

    with table_tab:
        event_table = make_event_table(table_source_df)
        if event_table.empty:
            st.warning("No events match the current filters.")
        else:
            st.dataframe(event_table, use_container_width=True, hide_index=True, height=520)
            csv = event_table.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Download filtered events as CSV",
                csv,
                file_name=f"lila_black_{selected_map}_filtered_events.csv",
                mime="text/csv",
            )

    with summary_tab:
        if single_match:
            match_row = match_summary[match_summary["match_id"].eq(selected_match)].iloc[0]
            left, right = st.columns(2)
            with left:
                st.subheader("Selected match")
                st.write(
                    {
                        "map": match_row["map_id"],
                        "date": match_row["source_date"],
                        "match_id": match_row["match_id"],
                        "duration": match_row["duration_label"],
                        "players": int(match_row["players"]),
                        "humans": int(match_row["human_players"]),
                        "bots": int(match_row["bot_players"]),
                    }
                )
            with right:
                st.subheader("Match events")
                st.write(
                    {
                        "total_events": int(match_row["total_events"]),
                        "movement_rows": int(match_row["movement_rows"]),
                        "kills": int(match_row["kills"]),
                        "deaths": int(match_row["deaths"]),
                        "storm_deaths": int(match_row["storm_deaths"]),
                        "loot_events": int(match_row["loot_events"]),
                    }
                )
            st.subheader("Players in this match")
            player_rows = player_summary[player_summary["match_id"].eq(selected_match)]
            st.dataframe(player_rows, use_container_width=True, hide_index=True, height=360)
        else:
            st.subheader("Aggregate match summary")
            st.dataframe(scoped_summary, use_container_width=True, hide_index=True, height=520)

    with quality_tab:
        scoped_all = selected_df
        missing_coords = int(scoped_all[["x", "z"]].isna().any(axis=1).sum())
        out_of_bounds = int((~scoped_all["in_minimap_bounds"] & scoped_all[["x", "z"]].notna().all(axis=1)).sum())
        unknown_events = int(scoped_all["unknown_event"].sum())

        q1, q2, q3, q4 = st.columns(4)
        with q1:
            render_metric_card("Rows out of bounds", f"{out_of_bounds:,}", "clipped for plotting")
        with q2:
            render_metric_card("Missing x/z", f"{missing_coords:,}", "excluded from plotting")
        with q3:
            render_metric_card("Unknown events", f"{unknown_events:,}", "outside known taxonomy")
        with q4:
            render_metric_card("Files loaded", f"{report.get('loaded_files', scoped_all['source_file'].nunique()):,}", f"{report.get('failed_files', 0):,} failed")

        st.subheader("Minimap files")
        st.dataframe(minimap_status(ROOT), use_container_width=True, hide_index=True)

        st.subheader("Processing report")
        st.json(report or {"note": "No processing_report.json was found; summaries were loaded from parquet."})

        st.subheader("Event values in current scope")
        event_counts = scoped_all["event"].value_counts().reset_index()
        event_counts.columns = ["event", "rows"]
        st.dataframe(event_counts, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()

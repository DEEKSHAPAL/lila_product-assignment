"""Plotly minimap rendering for Streamlit."""

from __future__ import annotations

import base64
from html import escape
from io import BytesIO
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from PIL import Image

from src.config import HEATMAP_EVENT_GROUPS, IMAGE_SIZE, MAP_CONFIG
from src.utils import short_id


def _image_as_data_uri(image_path: Path) -> str:
    image = Image.open(image_path)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def add_minimap_background(fig: go.Figure, project_root: Path, map_id: str) -> None:
    """Add the correct minimap image below all telemetry traces."""
    if map_id not in MAP_CONFIG:
        raise ValueError(f"Unknown map_id: {map_id}")
    image_path = project_root / "minimaps" / MAP_CONFIG[map_id]["image"]
    if not image_path.exists():
        raise FileNotFoundError(f"Missing minimap image: {image_path}")

    fig.add_layout_image(
        dict(
            source=_image_as_data_uri(image_path),
            xref="x",
            yref="y",
            x=0,
            y=0,
            sizex=IMAGE_SIZE,
            sizey=IMAGE_SIZE,
            xanchor="left",
            yanchor="top",
            sizing="stretch",
            opacity=1,
            layer="below",
        )
    )


def _filtered_visible_players(df: pd.DataFrame, show_humans: bool, show_bots: bool) -> pd.DataFrame:
    if show_humans and show_bots:
        return df
    if show_humans:
        return df[df["player_type"].eq("Human")]
    if show_bots:
        return df[df["player_type"].eq("Bot")]
    return df.iloc[0:0]


def format_hover_text(row: pd.Series) -> str:
    """Build a readable hover label for event markers."""
    return (
        f"<b>{escape(str(row.get('event_display', row.get('event', ''))))}</b>"
        f"<br>Player: {escape(short_id(row.get('user_id', ''), 10))}"
        f"<br>Type: {escape(str(row.get('player_type', '')))}"
        f"<br>Time: {escape(str(row.get('match_time_label', '')))}"
        f"<br>World x/z: {float(row.get('x', 0)):.1f}, {float(row.get('z', 0)):.1f}"
        f"<br>Pixel x/y: {float(row.get('pixel_x', 0)):.1f}, {float(row.get('pixel_y', 0)):.1f}"
        f"<br>Map: {escape(str(row.get('map_id', '')))}"
        f"<br>Match: {escape(str(row.get('match_id', '')))}"
    )


def add_heatmap_layer(
    fig: go.Figure,
    df: pd.DataFrame,
    heatmap_mode: str,
    bins: int = 80,
    opacity: float = 0.45,
) -> None:
    """Add a 2D histogram layer for traffic or event concentration."""
    if heatmap_mode == "None" or df.empty:
        return

    events = HEATMAP_EVENT_GROUPS.get(heatmap_mode, set())
    if not events:
        return

    heat_df = df[df["event"].isin(events) & df["in_minimap_bounds"]].dropna(subset=["pixel_x", "pixel_y"])
    if heat_df.empty:
        return

    hist, x_edges, y_edges = np.histogram2d(
        heat_df["pixel_x"].to_numpy(),
        heat_df["pixel_y"].to_numpy(),
        bins=bins,
        range=[[0, IMAGE_SIZE], [0, IMAGE_SIZE]],
    )
    x_centers = (x_edges[:-1] + x_edges[1:]) / 2
    y_centers = (y_edges[:-1] + y_edges[1:]) / 2
    colorscale = {
        "Traffic": "Turbo",
        "Kills": "Reds",
        "Deaths": "Greys",
        "Storm Deaths": "Purples",
        "Loot": "Viridis",
    }.get(heatmap_mode, "Turbo")

    fig.add_trace(
        go.Heatmap(
            x=x_centers,
            y=y_centers,
            z=hist.T,
            colorscale=colorscale,
            opacity=opacity,
            showscale=True,
            colorbar=dict(title=heatmap_mode, len=0.45, thickness=12),
            hovertemplate=f"{heatmap_mode}<br>x=%{{x:.0f}} y=%{{y:.0f}}<br>rows=%{{z:.0f}}<extra></extra>",
            name=f"{heatmap_mode} heatmap",
        )
    )


def add_player_paths(
    fig: go.Figure,
    df: pd.DataFrame,
    show_humans: bool = True,
    show_bots: bool = True,
    max_players: int = 80,
) -> int:
    """Draw one movement path trace per visible player."""
    if df.empty:
        return 0

    movement = _filtered_visible_players(df, show_humans, show_bots)
    movement = movement[movement["is_movement"]].dropna(subset=["plot_pixel_x", "plot_pixel_y"])
    if movement.empty:
        return 0

    player_order = movement.groupby("user_id").size().sort_values(ascending=False).head(max_players).index
    movement = movement[movement["user_id"].isin(player_order)].sort_values("match_time_s")

    legend_seen: set[str] = set()
    traces = 0
    for user_id, group in movement.groupby("user_id", sort=False):
        if len(group) < 2:
            continue
        player_type = str(group["player_type"].iloc[0])
        color = "#4da3ff" if player_type == "Human" else "#ffb15c"
        dash = "solid" if player_type == "Human" else "dash"
        legend_name = f"{player_type} path"
        showlegend = legend_name not in legend_seen
        legend_seen.add(legend_name)

        fig.add_trace(
            go.Scatter(
                x=group["plot_pixel_x"],
                y=group["plot_pixel_y"],
                mode="lines",
                name=legend_name,
                showlegend=showlegend,
                line=dict(color=color, width=2 if player_type == "Human" else 1.5, dash=dash),
                opacity=0.82 if player_type == "Human" else 0.55,
                hovertemplate=(
                    f"{legend_name}<br>Player: {short_id(user_id, 10)}"
                    "<br>x=%{x:.0f} y=%{y:.0f}<extra></extra>"
                ),
            )
        )
        traces += 1
    return traces


def _marker_style(group_name: str) -> dict[str, object]:
    styles = {
        "Kill": dict(symbol="star", color="#ff3b30", size=13, line=dict(color="#ffffff", width=1)),
        "Death": dict(symbol="x", color="#050505", size=12, line=dict(color="#ffffff", width=1)),
        "Storm": dict(symbol="diamond", color="#b36bff", size=11, line=dict(color="#ffffff", width=1)),
        "Loot": dict(symbol="circle", color="#a6f04d", size=8, line=dict(color="#1d2b13", width=1)),
    }
    return styles[group_name]


def add_event_markers(
    fig: go.Figure,
    df: pd.DataFrame,
    enabled_groups: Iterable[str],
    show_humans: bool = True,
    show_bots: bool = True,
) -> None:
    """Draw combat, storm, and loot markers."""
    if df.empty:
        return
    enabled = set(enabled_groups)
    marker_df = _filtered_visible_players(df, show_humans, show_bots)
    marker_df = marker_df[marker_df["event_group"].isin(enabled)].dropna(subset=["plot_pixel_x", "plot_pixel_y"])
    if marker_df.empty:
        return

    for group_name in ["Kill", "Death", "Storm", "Loot"]:
        group = marker_df[marker_df["event_group"].eq(group_name)]
        if group.empty:
            continue
        fig.add_trace(
            go.Scatter(
                x=group["plot_pixel_x"],
                y=group["plot_pixel_y"],
                mode="markers",
                name=group_name,
                marker=_marker_style(group_name),
                text=[format_hover_text(row) for _, row in group.iterrows()],
                hovertemplate="%{text}<extra></extra>",
            )
        )


def create_map_figure(
    df: pd.DataFrame,
    map_id: str,
    project_root: Path,
    heatmap_mode: str = "None",
    show_humans: bool = True,
    show_bots: bool = True,
    enabled_event_groups: Iterable[str] | None = None,
    draw_paths: bool = True,
    path_df: pd.DataFrame | None = None,
    marker_df: pd.DataFrame | None = None,
    heatmap_df: pd.DataFrame | None = None,
    height: int = 790,
    max_path_players: int = 80,
) -> tuple[go.Figure, dict[str, int]]:
    """Create the complete minimap figure and return lightweight render stats."""
    enabled_event_groups = enabled_event_groups or ["Kill", "Death", "Storm", "Loot"]
    path_source = path_df if path_df is not None else df
    marker_source = marker_df if marker_df is not None else df
    heat_source = heatmap_df if heatmap_df is not None else df

    fig = go.Figure()
    add_minimap_background(fig, project_root, map_id)
    add_heatmap_layer(fig, heat_source, heatmap_mode)

    path_traces = 0
    if draw_paths:
        path_traces = add_player_paths(fig, path_source, show_humans, show_bots, max_players=max_path_players)
    add_event_markers(fig, marker_source, enabled_event_groups, show_humans, show_bots)

    fig.update_xaxes(range=[0, IMAGE_SIZE], visible=False, constrain="domain")
    fig.update_yaxes(range=[IMAGE_SIZE, 0], visible=False, scaleanchor="x", scaleratio=1)
    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=20, b=0),
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.01,
            xanchor="left",
            x=0,
            bgcolor="rgba(14,17,23,0.7)",
            font=dict(color="#f2f4f8"),
        ),
    )
    return fig, {"path_traces": path_traces}

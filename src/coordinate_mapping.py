"""Coordinate conversion from LILA BLACK world positions to minimap pixels."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from src.config import IMAGE_SIZE, MAP_CONFIG


def world_to_minimap(x: float, z: float, map_id: str) -> tuple[float, float, float, float, bool]:
    """Convert world x/z coordinates into minimap u/v and pixel x/y.

    The source y coordinate is elevation and is intentionally ignored.
    """
    if map_id not in MAP_CONFIG:
        known = ", ".join(sorted(MAP_CONFIG))
        raise ValueError(f"Unknown map_id '{map_id}'. Expected one of: {known}")

    cfg = MAP_CONFIG[map_id]
    u = (float(x) - cfg["origin_x"]) / cfg["scale"]
    v = (float(z) - cfg["origin_z"]) / cfg["scale"]
    pixel_x = u * IMAGE_SIZE
    pixel_y = (1 - v) * IMAGE_SIZE
    in_bounds = 0 <= pixel_x <= IMAGE_SIZE and 0 <= pixel_y <= IMAGE_SIZE
    return u, v, pixel_x, pixel_y, in_bounds


def add_minimap_coordinates(df: pd.DataFrame) -> pd.DataFrame:
    """Add u/v, pixel coordinates, plotting coordinates, and bounds flags."""
    result = df.copy()
    for column in ["u", "v", "pixel_x", "pixel_y"]:
        result[column] = np.nan
    result["in_minimap_bounds"] = False

    if result.empty:
        result["plot_pixel_x"] = pd.Series(dtype="float64")
        result["plot_pixel_y"] = pd.Series(dtype="float64")
        return result

    result["x"] = pd.to_numeric(result["x"], errors="coerce")
    result["z"] = pd.to_numeric(result["z"], errors="coerce")

    for map_id, cfg in MAP_CONFIG.items():
        mask = result["map_id"].eq(map_id) & result["x"].notna() & result["z"].notna()
        if not mask.any():
            continue
        u = (result.loc[mask, "x"] - cfg["origin_x"]) / cfg["scale"]
        v = (result.loc[mask, "z"] - cfg["origin_z"]) / cfg["scale"]
        result.loc[mask, "u"] = u
        result.loc[mask, "v"] = v
        result.loc[mask, "pixel_x"] = u * IMAGE_SIZE
        result.loc[mask, "pixel_y"] = (1 - v) * IMAGE_SIZE

    result["in_minimap_bounds"] = (
        result["pixel_x"].between(0, IMAGE_SIZE)
        & result["pixel_y"].between(0, IMAGE_SIZE)
    )
    result["plot_pixel_x"] = result["pixel_x"].clip(0, IMAGE_SIZE)
    result["plot_pixel_y"] = result["pixel_y"].clip(0, IMAGE_SIZE)
    return result


def validate_coordinate_mapping() -> dict[str, Any]:
    """Return validation values for the documented AmbroseValley sample."""
    u, v, pixel_x, pixel_y, in_bounds = world_to_minimap(
        x=-301.45,
        z=-355.55,
        map_id="AmbroseValley",
    )
    return {
        "map_id": "AmbroseValley",
        "u": u,
        "v": v,
        "pixel_x": pixel_x,
        "pixel_y": pixel_y,
        "in_minimap_bounds": in_bounds,
        "expected_pixel_x": 78,
        "expected_pixel_y": 890,
        "within_tolerance": abs(pixel_x - 78) <= 2 and abs(pixel_y - 890) <= 2,
    }


from __future__ import annotations

import math

import pytest

from src.config import MAP_CONFIG
from src.coordinate_mapping import world_to_minimap


def test_ambrose_readme_sample_maps_near_expected_pixels() -> None:
    _, _, pixel_x, pixel_y, in_bounds = world_to_minimap(
        x=-301.45,
        z=-355.55,
        map_id="AmbroseValley",
    )

    assert in_bounds is True
    assert pixel_x == pytest.approx(78, abs=2)
    assert pixel_y == pytest.approx(890, abs=2)


def test_all_maps_produce_numeric_output() -> None:
    for map_id, cfg in MAP_CONFIG.items():
        x = cfg["origin_x"] + cfg["scale"] / 2
        z = cfg["origin_z"] + cfg["scale"] / 2
        u, v, pixel_x, pixel_y, in_bounds = world_to_minimap(x=x, z=z, map_id=map_id)

        assert all(math.isfinite(value) for value in [u, v, pixel_x, pixel_y])
        assert in_bounds is True
        assert pixel_x == pytest.approx(512, abs=0.01)
        assert pixel_y == pytest.approx(512, abs=0.01)


def test_unknown_map_raises_clear_error() -> None:
    with pytest.raises(ValueError, match="Unknown map_id"):
        world_to_minimap(x=0, z=0, map_id="MissingMap")

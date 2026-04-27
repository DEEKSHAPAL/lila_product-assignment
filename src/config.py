"""Project-wide configuration for data processing and visualization."""

from __future__ import annotations

IMAGE_SIZE = 1024

DATA_FOLDERS = [
    "February_10",
    "February_11",
    "February_12",
    "February_13",
    "February_14",
]

MINIMAP_DIR = "minimaps"
PROCESSED_DIR = "data_processed"

MAP_CONFIG = {
    "AmbroseValley": {
        "scale": 900,
        "origin_x": -370,
        "origin_z": -473,
        "image": "AmbroseValley_Minimap.png",
    },
    "GrandRift": {
        "scale": 581,
        "origin_x": -290,
        "origin_z": -290,
        "image": "GrandRift_Minimap.png",
    },
    "Lockdown": {
        "scale": 1000,
        "origin_x": -500,
        "origin_z": -500,
        "image": "Lockdown_Minimap.jpg",
    },
}

KNOWN_EVENTS = {
    "Position",
    "BotPosition",
    "Kill",
    "Killed",
    "BotKill",
    "BotKilled",
    "KilledByStorm",
    "Loot",
}

MOVEMENT_EVENTS = {"Position", "BotPosition"}
KILL_EVENTS = {"Kill", "BotKill"}
DEATH_EVENTS = {"Killed", "BotKilled"}
STORM_EVENTS = {"KilledByStorm"}
LOOT_EVENTS = {"Loot"}

EVENT_GROUPS = {
    "Position": "Movement",
    "BotPosition": "Movement",
    "Kill": "Kill",
    "BotKill": "Kill",
    "Killed": "Death",
    "BotKilled": "Death",
    "KilledByStorm": "Storm",
    "Loot": "Loot",
}

EVENT_CATEGORIES = {
    "Position": "Movement",
    "BotPosition": "Movement",
    "Kill": "Combat",
    "BotKill": "Combat",
    "Killed": "Combat",
    "BotKilled": "Combat",
    "KilledByStorm": "Environment",
    "Loot": "Item",
}

EVENT_DISPLAY = {
    "Position": "Player position",
    "BotPosition": "Bot position",
    "Kill": "Human kill",
    "Killed": "Human death",
    "BotKill": "Bot kill",
    "BotKilled": "Killed by bot",
    "KilledByStorm": "Storm death",
    "Loot": "Loot pickup",
}

HEATMAP_EVENT_GROUPS = {
    "None": set(),
    "Traffic": MOVEMENT_EVENTS,
    "Kills": KILL_EVENTS,
    "Deaths": DEATH_EVENTS,
    "Storm Deaths": STORM_EVENTS,
    "Loot": LOOT_EVENTS,
}


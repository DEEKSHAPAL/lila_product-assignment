"""Small utility helpers shared by scripts and the Streamlit app."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def format_match_time(seconds: Any) -> str:
    """Format seconds as mm:ss or h:mm:ss for long matches."""
    try:
        raw_seconds = max(0.0, float(seconds))
    except (TypeError, ValueError):
        raw_seconds = 0.0

    if 0 < raw_seconds < 10:
        return f"00:{raw_seconds:05.2f}"

    total_seconds = int(round(raw_seconds))

    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def short_id(value: Any, chars: int = 8) -> str:
    """Return a compact display version of an identifier."""
    if value is None:
        return ""
    text = str(value)
    if len(text) <= chars + 3:
        return text
    return f"{text[:chars]}..."


def safe_numeric_check(value: Any) -> bool:
    """Return True when a user id looks like the short numeric bot ids."""
    if value is None:
        return False
    text = str(value).strip()
    return text.isdigit() and len(text) > 0


def ensure_directory(path: Path) -> Path:
    """Create a directory if needed and return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def date_sort_key(value: Any) -> tuple[int, str]:
    """Sort February_10 ... February_14 numerically while keeping fallbacks stable."""
    text = str(value)
    try:
        return int(text.split("_")[-1]), text
    except (ValueError, IndexError):
        return 999, text


def clean_number(value: Any, digits: int = 1) -> str:
    """Format a numeric value for compact UI and markdown evidence."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "0"
    if abs(number) >= 100:
        return f"{number:,.0f}"
    return f"{number:,.{digits}f}"

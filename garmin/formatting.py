"""Pure formatting functions for Garmin sync tools.

No side effects, no state — just formatting and status interpretation.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from config import WEEKDAYS_RU, Thresholds as T


# ─── Pace ────────────────────────────────────────────────────────────────────

def format_pace(speed_mps: float) -> str:
    """Convert speed (m/s) to pace string (min:sec/km)."""
    if speed_mps <= 0:
        return "---"
    pace_min = 1000 / (speed_mps * 60)
    minutes = int(pace_min)
    seconds = int((pace_min - minutes) * 60)
    return f"{minutes}:{seconds:02d}"


def format_pace_from_distance(duration_sec: float, distance_m: float) -> str:
    """Calculate pace from total duration and distance."""
    if not duration_sec or not distance_m:
        return "---"
    pace_min = (duration_sec / 60) / (distance_m / 1000)
    return f"{int(pace_min)}:{int((pace_min % 1) * 60):02d}"


# ─── Dates ───────────────────────────────────────────────────────────────────

def format_date_ru(target_date: date) -> str:
    """Format date as 'DD.MM (DayOfWeek)' in Russian."""
    return f"{target_date.strftime('%d.%m')} ({WEEKDAYS_RU[target_date.weekday()]})"


# ─── Numeric ─────────────────────────────────────────────────────────────────

def fmt(value: Any, decimals: int = 1) -> str:
    """Format value as float with fixed decimals, or '---' on failure."""
    if value is None:
        return "---"
    try:
        return f"{float(value):.{decimals}f}"
    except (ValueError, TypeError):
        return "---"


def fmt_int(value: Any) -> str:
    """Format value as int, or '---' on failure."""
    if value is None:
        return "---"
    try:
        return str(int(round(float(value))))
    except (ValueError, TypeError):
        return "---"


# ─── Status interpreters ─────────────────────────────────────────────────────

def interpret_hrv(hrv_ms: float | None) -> str:
    """Map HRV value to status label."""
    if hrv_ms is None:
        return "---"
    if hrv_ms >= T.HRV_BALANCED:
        return "Balanced"
    if hrv_ms >= T.HRV_UNBALANCED:
        return "Unbalanced"
    return "Low"


def interpret_rhr(rhr: int | None) -> str:
    """Map resting heart rate to status bracket."""
    if rhr is None:
        return "---"
    if rhr <= T.RHR_GREEN_MAX:
        return "[OK]"
    if rhr <= T.RHR_YELLOW_MAX:
        return "[C]"
    return "[!]"


def interpret_body_battery(bb: int | None) -> str:
    """Map body battery at wake to readiness bracket."""
    if bb is None:
        return "---"
    if bb >= T.BB_GREEN_MIN:
        return "[G]"
    if bb >= T.BB_YELLOW_MIN:
        return "[Y]"
    return "[R]"

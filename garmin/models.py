"""Structured data models for Garmin sync tools.

Provides typed dataclasses instead of raw dicts for consistency and IDE support.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DailyMetrics:
    """Aggregated health metrics for a single day."""

    rhr: int | None = None
    hrv_ms: float | None = None
    sleep_total_h: float | None = None
    sleep_deep_h: float | None = None
    body_battery_wake: int | None = None
    stress: int | None = None
    body_battery_charge: int | None = None
    body_battery_drain: int | None = None
    steps: int | None = None


@dataclass
class ActivitySummary:
    """Summary fields from an activity list entry."""

    activity_id: str
    activity_type: str
    start_time: str
    distance_m: float
    duration_s: float
    avg_hr: int | None = None
    max_hr: int | None = None
    avg_cadence: float | None = None
    vert_osc_cm: float | None = None
    ground_contact_ms: int | None = None
    elevation_gain_m: float = 0
    calories: int | None = None
    training_effect: float | None = None
    hr_zones: dict[str, float] = field(default_factory=dict)


@dataclass
class LapData:
    """Single lap/interval from an activity."""

    lap_index: int | None = None
    start_time: str = ""
    distance_m: float = 0
    duration_s: float = 0
    moving_duration_s: float = 0
    avg_speed_mps: float = 0
    max_speed_mps: float = 0
    avg_hr: int | None = None
    max_hr: int | None = None
    avg_cadence: float = 0
    max_cadence: int | None = None
    elevation_gain_m: float = 0
    elevation_loss_m: float = 0
    calories: int | None = None
    avg_power_w: int | None = None
    max_power_w: int | None = None
    vert_osc_cm: float = 0
    ground_contact_ms: int | None = None
    stride_length_cm: float = 0
    start_lat: float | None = None
    start_lon: float | None = None
    end_lat: float | None = None
    end_lon: float | None = None


@dataclass
class TelemetryPoint:
    """Single telemetry sample from activity detail."""

    timestamp_ms: float | None = None
    hr_bpm: float | None = None
    speed_mps: float | None = None
    gap_mps: float | None = None
    cadence_spm: float | None = None
    stride_cm: float | None = None
    vert_osc_cm: float | None = None
    ground_contact_ms: float | None = None
    vert_ratio: float | None = None
    elevation_m: float | None = None
    power_w: float | None = None
    body_battery: float | None = None
    stamina_available: float | None = None
    stamina_potential: float | None = None
    resp_rate: float | None = None
    lat: float | None = None
    lon: float | None = None
    double_cadence: float | None = None
    vert_speed_mps: float | None = None
    perf_condition: float | None = None
    distance_m: float | None = None
    duration_s: float | None = None
    moving_duration_s: float | None = None
    elapsed_s: float | None = None
    accum_power: float | None = None


@dataclass
class WeatherData:
    """Weather data for an activity."""

    lat: float
    lon: float
    date: str
    temperature_avg: float | None = None
    temperature_min: float | None = None
    temperature_max: float | None = None
    humidity_avg: int | None = None
    precipitation_total: float | None = None
    wind_avg_kmh: float | None = None
    wind_gusts_max_kmh: float | None = None
    hourly: dict[str, list[Any]] = field(default_factory=dict)

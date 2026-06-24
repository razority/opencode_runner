"""Analysis functions for activity telemetry and weather impact.

Pure computation — no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from formatting import format_pace
from models import TelemetryPoint, WeatherData


@dataclass
class KmSegment:
    """Aggregated metrics for a single kilometer."""

    km: int
    pace: str
    hr: int
    max_hr: int
    cadence: int
    ground_contact: int
    stride: float
    vert_osc: float
    body_battery: int
    seg_time_s: int
    seg_dist_m: float
    points: int


def analyze_per_km(telemetry: list[TelemetryPoint], total_distance_m: float) -> list[KmSegment]:
    """Group telemetry points by kilometer and compute avg metrics per km."""
    if not telemetry:
        return []

    total_km = int(total_distance_m / 1000)
    results: list[KmSegment] = []

    for km in range(total_km + 1):
        km_start = km * 1000
        km_end = (km + 1) * 1000 if km < total_km else total_distance_m + 1

        points = [
            pt for pt in telemetry
            if pt.distance_m is not None and km_start <= pt.distance_m < km_end
        ]

        if not points:
            continue

        n = len(points)
        avg_speed = sum(pt.speed_mps or 0 for pt in points) / n
        avg_hr = sum(pt.hr_bpm or 0 for pt in points) / n
        avg_cadence = sum(pt.double_cadence or 0 for pt in points) / n
        avg_gc = sum(pt.ground_contact_ms or 0 for pt in points) / n
        avg_stride = sum(pt.stride_cm or 0 for pt in points) / n
        avg_vert = sum(pt.vert_osc_cm or 0 for pt in points) / n
        avg_bb = sum(pt.body_battery or 0 for pt in points) / n
        max_hr = max((pt.hr_bpm or 0) for pt in points)

        ts_first = points[0].elapsed_s or 0
        ts_last = points[-1].elapsed_s or 0
        seg_time_s = ts_last - ts_first
        seg_dist_m = (points[-1].distance_m or 0) - (points[0].distance_m or 0)

        results.append(KmSegment(
            km=km,
            pace=format_pace(avg_speed),
            hr=round(avg_hr),
            max_hr=round(max_hr),
            cadence=round(avg_cadence),
            ground_contact=round(avg_gc),
            stride=round(avg_stride, 1),
            vert_osc=round(avg_vert, 1),
            body_battery=round(avg_bb),
            seg_time_s=round(seg_time_s),
            seg_dist_m=round(seg_dist_m),
            points=n,
        ))

    return results


@dataclass
class WeatherAdjustment:
    """Pace adjustment due to weather conditions."""

    sec_per_km: int
    reasons: list[str]
    temp: float | None
    humidity: float | None
    wind: float | None
    gusts: float | None


def calc_weather_adjustment(weather: WeatherData | None) -> WeatherAdjustment | None:
    """Calculate pace adjustment (sec/km) based on weather.

    Uses the Jack Daniels / Pete Riegel model:
    - Temperature: optimal 10-15C, penalty above 15C and below 5C
    - Humidity: penalty above 80%
    - Wind: headwind penalty (conservative assumption: 50% headwind)
    """
    if not weather or weather.temperature_avg is None:
        return None

    temp = weather.temperature_avg
    humidity = weather.humidity_avg
    wind = weather.wind_avg_kmh
    gusts = weather.wind_gusts_max_kmh

    adj_total = 0
    reasons: list[str] = []

    # Temperature
    if temp > 25:
        adj_temp = (temp - 25) * 3.0 + 15
        reasons.append(f"temp +{adj_temp:.0f}")
    elif temp > 15:
        adj_temp = (temp - 15) * 1.5
        reasons.append(f"temp +{adj_temp:.0f}")
    elif temp < 5:
        adj_temp = (5 - temp) * 1.0
        reasons.append(f"temp +{adj_temp:.0f}")
    else:
        adj_temp = 0

    adj_total += adj_temp

    # Humidity
    if humidity and humidity > 80:
        adj_hum = (humidity - 80) * 0.3
        adj_total += adj_hum
        reasons.append(f"hum +{adj_hum:.0f}")

    # Wind (assume 50% headwind)
    if wind and wind > 5:
        headwind_eff = wind * 0.5
        adj_wind = headwind_eff * 1.2
        adj_total += adj_wind
        reasons.append(f"wind +{adj_wind:.0f}")

    return WeatherAdjustment(
        sec_per_km=round(adj_total),
        reasons=reasons,
        temp=temp,
        humidity=humidity,
        wind=wind,
        gusts=gusts,
    )

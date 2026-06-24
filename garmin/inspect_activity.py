#!/usr/bin/env python3
"""Fetch detailed activity data from Garmin Connect and save as JSON.

Usage:
    python inspect_activity.py                  # latest activity
    python inspect_activity.py --date 2026-06-24
    python inspect_activity.py --days 3
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

from client import GarminClient
from models import ActivitySummary, LapData, TelemetryPoint, WeatherData
from weather import WeatherService


def activity_to_dict(
    raw_summary: dict,
    activity_id: str,
    laps: list[LapData],
    events: list[dict],
    telemetry: list[TelemetryPoint],
    weather: WeatherData | None,
) -> dict:
    """Convert structured models to a JSON-serializable dict."""
    summary_dto = raw_summary.get("summaryDTO", {})

    telemetry_dicts = [
        {
            k: v for k, v in {
                "timestamp_ms": pt.timestamp_ms,
                "hr_bpm": pt.hr_bpm,
                "speed_mps": pt.speed_mps,
                "gap_mps": pt.gap_mps,
                "cadence_spm": pt.cadence_spm,
                "stride_cm": pt.stride_cm,
                "vert_osc_cm": pt.vert_osc_cm,
                "ground_contact_ms": pt.ground_contact_ms,
                "vert_ratio": pt.vert_ratio,
                "elevation_m": pt.elevation_m,
                "power_w": pt.power_w,
                "body_battery": pt.body_battery,
                "stamina_available": pt.stamina_available,
                "stamina_potential": pt.stamina_potential,
                "resp_rate": pt.resp_rate,
                "lat": pt.lat,
                "lon": pt.lon,
                "double_cadence": pt.double_cadence,
                "vert_speed_mps": pt.vert_speed_mps,
                "perf_condition": pt.perf_condition,
                "distance_m": pt.distance_m,
                "duration_s": pt.duration_s,
                "moving_duration_s": pt.moving_duration_s,
                "elapsed_s": pt.elapsed_s,
                "accum_power": pt.accum_power,
            }.items()
            if v is not None
        }
        for pt in telemetry
    ]

    laps_dicts = [
        {
            "lap_index": lap.lap_index,
            "start_time": lap.start_time,
            "distance_m": lap.distance_m,
            "duration_s": lap.duration_s,
            "moving_duration_s": lap.moving_duration_s,
            "avg_speed_mps": lap.avg_speed_mps,
            "max_speed_mps": lap.max_speed_mps,
            "avg_hr": lap.avg_hr,
            "max_hr": lap.max_hr,
            "avg_cadence": lap.avg_cadence,
            "max_cadence": lap.max_cadence,
            "elevation_gain_m": lap.elevation_gain_m,
            "elevation_loss_m": lap.elevation_loss_m,
            "calories": lap.calories,
            "avg_power_w": lap.avg_power_w,
            "max_power_w": lap.max_power_w,
            "vert_osc_cm": lap.vert_osc_cm,
            "ground_contact_ms": lap.ground_contact_ms,
            "stride_length_cm": lap.stride_length_cm,
            "coordinates": {
                "start": {"lat": lap.start_lat, "lon": lap.start_lon},
                "end": {"lat": lap.end_lat, "lon": lap.end_lon},
            },
        }
        for lap in laps
    ]

    weather_dict = None
    if weather:
        weather_dict = {
            "coordinates": {"lat": weather.lat, "lon": weather.lon},
            "date": weather.date,
            "summary": {
                "temperature_avg": weather.temperature_avg,
                "temperature_min": weather.temperature_min,
                "temperature_max": weather.temperature_max,
                "humidity_avg": weather.humidity_avg,
                "precipitation_total": weather.precipitation_total,
                "wind_avg_kmh": weather.wind_avg_kmh,
                "wind_gusts_max_kmh": weather.wind_gusts_max_kmh,
            },
            "hourly": weather.hourly,
        }

    result = {
        "activity_id": activity_id,
        "activity_type": raw_summary.get("activityTypeDTO", {}).get("typeKey"),
        "start_time": summary_dto.get("startTimeLocal"),
        "summary": {
            "distance_m": round(summary_dto.get("distance", 0), 1),
            "duration_s": round(summary_dto.get("duration", 0), 2),
            "moving_duration_s": round(summary_dto.get("movingDuration", 0), 2),
            "avg_speed_mps": round(summary_dto.get("averageSpeed", 0), 3),
            "avg_hr": summary_dto.get("averageHR"),
            "max_hr": summary_dto.get("maxHR"),
            "calories": summary_dto.get("calories"),
            "elevation_gain_m": round(summary_dto.get("elevationGain", 0), 1),
            "training_effect": summary_dto.get("trainingEffect"),
            "avg_cadence": round(summary_dto.get("averageRunCadence", 0), 1),
            "vert_osc_cm": round(summary_dto.get("verticalOscillation", 0), 2),
            "ground_contact_ms": summary_dto.get("groundContactTime"),
            "stride_length_cm": round(summary_dto.get("strideLength", 0), 1),
        },
        "hr_zones": {
            f"Z{i}": round(summary_dto.get(f"hrTimeInZone_{i}", 0) or 0, 1)
            for i in range(1, 6)
        },
        "laps": laps_dicts,
        "events": events,
        "telemetry_points": len(telemetry_dicts),
        "telemetry": telemetry_dicts,
    }

    if weather_dict:
        result["weather"] = weather_dict

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch detailed Garmin activity data")
    parser.add_argument("--date", type=str, default=None, help="Date in YYYY-MM-DD format")
    parser.add_argument("--days", type=int, default=1, help="Number of days to look back")
    parser.add_argument("--output", type=str, default=None, help="Output JSON file path")
    parser.add_argument("--no-weather", action="store_true", help="Skip weather data fetch")
    args = parser.parse_args()

    client = GarminClient.from_env()

    # Determine date range
    if args.date:
        target = date.fromisoformat(args.date)
        start, end = target, target + timedelta(days=1)
    else:
        end = date.today()
        start = end - timedelta(days=args.days)

    # Find matching activities
    matching = client.find_activities(
        datetime.combine(start, datetime.min.time()),
        datetime.combine(end, datetime.max.time()),
    )

    if not matching:
        print("No activities for the specified period.", file=sys.stderr)
        sys.exit(0)

    # Fetch full details for each activity
    weather_svc = WeatherService()
    results = []

    for act in matching:
        aid = act.activity_id
        print(f"  Loading activity {aid}...", file=sys.stderr)

        raw = client.get_activity_detail(aid)
        laps = client.get_activity_laps(aid)
        events = client.get_activity_events(aid)
        telemetry = client.get_activity_telemetry(aid)

        # Weather enrichment
        weather = None
        if not args.no_weather:
            summary_dto = raw.get("summaryDTO", {})
            lat = summary_dto.get("startLatitude")
            lon = summary_dto.get("startLongitude")
            start_time = summary_dto.get("startTimeLocal")
            end_time = summary_dto.get("endTimeLocal") or start_time
            if lat and lon and start_time:
                print(f"  Loading weather ({lat:.2f}, {lon:.2f})...", file=sys.stderr)
                weather = weather_svc.get_for_activity(lat, lon, start_time, end_time)

        results.append(activity_to_dict(raw, aid, laps, events, telemetry, weather))

    # Output
    output = results[0] if len(results) == 1 else results
    json_str = json.dumps(output, indent=2, ensure_ascii=False)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(json_str)
        print(f"Saved to {args.output}", file=sys.stderr)
    else:
        print(json_str)


if __name__ == "__main__":
    main()

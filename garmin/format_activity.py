#!/usr/bin/env python3
"""Pretty-print a JSON activity file from inspect_activity.py.

Usage:
    python format_activity.py <activity.json>
    python format_activity.py <activity.json> --label "Morning Run"
    python format_activity.py <activity.json> --sample 10
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

sys.stdout.reconfigure(encoding="utf-8")

from analysis import KmSegment, WeatherAdjustment, analyze_per_km, calc_weather_adjustment
from formatting import fmt, fmt_int, format_pace
from models import TelemetryPoint, WeatherData


# ─── Section renderers ───────────────────────────────────────────────────────

def print_summary(data: dict, label: str) -> None:
    """Print the overall activity summary block."""
    s = data.get("summary", {})
    dist_km = s.get("distance_m", 0) / 1000
    dur_s = s.get("duration_s", 0)
    dur_m = dur_s / 60
    pace = format_pace(s.get("avg_speed_mps", 0))
    te = s.get("training_effect", 0)
    te_rounded = round(te, 1) if isinstance(te, (int, float)) else te

    print(f"\n{'=' * 60}")
    print(label)
    print("=" * 60)
    print(f"Distance:     {dist_km:.2f} km")
    print(f"Time:         {dur_m:.1f} min ({dur_s:.0f}s)")
    print(f"Pace:         {pace}/km")
    print(f"Avg HR:       {fmt_int(s.get('avg_hr'))}")
    print(f"Max HR:       {fmt_int(s.get('max_hr'))}")
    print(f"Calories:     {fmt_int(s.get('calories'))}")
    print(f"Elevation:    {fmt(s.get('elevation_gain_m'), 0)} m")
    print(f"Cadence:      {fmt(s.get('avg_cadence'))}")
    print(f"Vert. osc.:   {fmt(s.get('vert_osc_cm'))} cm")
    print(f"Ground cont.: {fmt_int(s.get('ground_contact_ms'))} ms")
    print(f"Stride:       {fmt(s.get('stride_length_cm'))} cm")
    print(f"TE:           {te_rounded}")
    print(f"Power:        {fmt(s.get('avg_power_w'))} W")

    # Weather-adjusted pace
    weather_raw = data.get("weather")
    if weather_raw:
        weather = _dict_to_weather(weather_raw)
        adj = calc_weather_adjustment(weather)
        if adj and adj.sec_per_km != 0:
            avg_speed = s.get("avg_speed_mps", 0)
            if avg_speed > 0:
                raw_pace_sec = 1000 / avg_speed
                adj_pace_sec = raw_pace_sec + adj.sec_per_km
                adj_pace_min = adj_pace_sec / 60
                adj_m = int(adj_pace_min)
                adj_s = int((adj_pace_min - adj_m) * 60)
                sign = "+" if adj.sec_per_km > 0 else ""
                print(f"Pace (weather): {adj_m}:{adj_s:02d}/km ({sign}{adj.sec_per_km} s/km)")


def print_weather(weather_raw: dict | None) -> None:
    """Print weather summary and hourly forecast during the activity."""
    if not weather_raw:
        return

    summary = weather_raw.get("summary", {})
    hourly = weather_raw.get("hourly", {})

    print(f"\nWeather:")
    print(f"  Temperature: {fmt(summary.get('temperature_avg'))}C "
          f"(min {fmt(summary.get('temperature_min'))} / max {fmt(summary.get('temperature_max'))})")
    print(f"  Humidity:    {fmt_int(summary.get('humidity_avg'))}%")
    print(f"  Precip:      {fmt(summary.get('precipitation_total'))} mm")
    print(f"  Wind:        {fmt(summary.get('wind_avg_kmh'))} km/h "
          f"(gusts {fmt(summary.get('wind_gusts_max_kmh'))} km/h)")

    times = hourly.get("time", [])
    temps = hourly.get("temperature_2m", [])
    humidity = hourly.get("relative_humidity_2m", [])
    precip = hourly.get("precipitation", [])
    wind = hourly.get("wind_speed_10m", [])

    if times:
        print(f"\n  Hourly:")
        for i, t in enumerate(times):
            hour = t.split("T")[1][:5] if "T" in t else t
            temp = temps[i] if i < len(temps) else "---"
            hum = humidity[i] if i < len(humidity) else "---"
            prc = precip[i] if i < len(precip) else 0
            wnd = wind[i] if i < len(wind) else "---"
            prc_str = f" {prc}mm" if prc else ""
            print(f"    {hour}  {temp:>5}C  {hum:>3}%  {wnd:>5}km/h{prc_str}")


def print_laps(laps: list[dict]) -> None:
    """Print per-lap breakdown."""
    if not laps:
        return

    print(f"\nLaps ({len(laps)}):")
    for i, lap in enumerate(laps, 1):
        dist_km = lap.get("distance_m", 0) / 1000
        dur_min = lap.get("duration_s", 0) / 60
        pace = format_pace(lap.get("avg_speed_mps", 0))

        print(
            f"  L{i}: {dist_km:.2f}km {dur_min:.1f}min {pace}/km "
            f"HR={lap.get('avg_hr', '---')}-{lap.get('max_hr', '---')} "
            f"cad={fmt(lap.get('avg_cadence'))} "
            f"gc={fmt_int(lap.get('ground_contact_ms'))}ms "
            f"vert={fmt(lap.get('vert_osc_cm'))}cm "
            f"stride={fmt(lap.get('stride_length_cm'))}cm "
            f"P={fmt_int(lap.get('avg_power_w'))}W"
        )


def print_per_km(km_data: list[KmSegment]) -> None:
    """Print per-km analysis table."""
    if not km_data:
        return

    rows = [r for r in km_data if r.km > 0]
    if not rows:
        rows = km_data

    print(f"\nPer kilometer:")
    print(f"  km   pace    HR  max  cad  gc    stride vert  BB")
    print(f"  {'-' * 56}")

    for row in rows:
        gc_str = f"{row.ground_contact}" if row.ground_contact else "---"
        print(
            f"  {row.km:>3}  {row.pace}  {row.hr:>3}  {row.max_hr:>3}  {row.cadence:>3}  "
            f"{gc_str:>4}  {row.stride:>5}  {row.vert_osc:>4}  {row.body_battery:>3}"
        )

    if len(rows) > 1:
        avg_hr = sum(r.hr for r in rows) / len(rows)
        avg_cad = sum(r.cadence for r in rows) / len(rows)
        gc_vals = [r.ground_contact for r in rows if r.ground_contact]
        avg_gc = sum(gc_vals) / max(1, len(gc_vals)) if gc_vals else 0
        avg_stride = sum(r.stride for r in rows) / len(rows)
        print(f"  {'-' * 56}")
        print(
            f"  avg  {'':5}  {avg_hr:>3.0f}  {'':3}  {avg_cad:>3.0f}  "
            f"{avg_gc:>4.0f}  {avg_stride:>5.1f}"
        )


def print_telemetry_sample(telemetry_raw: list[dict], num_samples: int = 5) -> None:
    """Print a sample of telemetry points spread across the activity."""
    if not telemetry_raw:
        return

    n = len(telemetry_raw)
    print(f"\nTelemetry ({n} points):")

    if num_samples <= n:
        step = n // (num_samples - 1) if num_samples > 1 else 0
        indices = [min(i * step, n - 1) for i in range(num_samples)]
    else:
        indices = list(range(n))

    for idx in indices:
        pt = telemetry_raw[idx]
        hr = fmt_int(pt.get("hr_bpm"))
        pace = format_pace(pt.get("speed_mps", 0))
        cad = fmt_int(pt.get("double_cadence"))
        gc = fmt_int(pt.get("ground_contact_ms"))
        vo = fmt(pt.get("vert_osc_cm"))
        stamina = fmt_int(pt.get("stamina_available"))
        potential = fmt_int(pt.get("stamina_potential"))
        bb = fmt_int(pt.get("body_battery"))
        dist_km = pt.get("distance_m", 0) / 1000

        print(
            f"  @{dist_km:.1f}km: HR={hr} pace={pace}/km "
            f"cad={cad} gc={gc}ms vert={vo}cm "
            f"stam={stamina}/{potential} BB={bb}"
        )


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _dict_to_weather(d: dict) -> WeatherData:
    """Convert a weather dict back to WeatherData model."""
    s = d.get("summary", {})
    return WeatherData(
        lat=d.get("coordinates", {}).get("lat", 0),
        lon=d.get("coordinates", {}).get("lon", 0),
        date=d.get("date", ""),
        temperature_avg=s.get("temperature_avg"),
        temperature_min=s.get("temperature_min"),
        temperature_max=s.get("temperature_max"),
        humidity_avg=s.get("humidity_avg"),
        precipitation_total=s.get("precipitation_total"),
        wind_avg_kmh=s.get("wind_avg_kmh"),
        wind_gusts_max_kmh=s.get("wind_gusts_max_kmh"),
    )


def _render_activity(data: dict, label: str, args: argparse.Namespace) -> None:
    """Render a single activity."""
    print_summary(data, label)
    print_weather(data.get("weather"))
    print_laps(data.get("laps", []))
    if args.raw:
        print_telemetry_sample(data.get("telemetry", []), args.sample)
    else:
        total_dist = data.get("summary", {}).get("distance_m", 0)
        telemetry_raw = data.get("telemetry", [])
        # Convert raw dicts to TelemetryPoint for analysis
        telemetry_pts = [_dict_to_telemetry(pt) for pt in telemetry_raw]
        km_data = analyze_per_km(telemetry_pts, total_dist)
        print_per_km(km_data)


def _dict_to_telemetry(d: dict) -> TelemetryPoint:
    """Convert a telemetry dict to TelemetryPoint model."""
    return TelemetryPoint(**{k: d.get(k) for k in TelemetryPoint.__dataclass_fields__})


# ─── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pretty-print a Garmin activity JSON file"
    )
    parser.add_argument("json_file", help="Path to activity JSON from inspect_activity.py")
    parser.add_argument("--label", default="Training", help="Header label")
    parser.add_argument("--sample", type=int, default=5, help="Number of telemetry sample points")
    parser.add_argument("--per-km", action="store_true", default=True, help="Show per-km analysis")
    parser.add_argument("--raw", action="store_true", default=False, help="Show raw telemetry instead of per-km")
    args = parser.parse_args()

    with open(args.json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        for i, activity in enumerate(data):
            label = args.label if len(data) == 1 else f"{args.label} [{i + 1}]"
            _render_activity(activity, label, args)
    else:
        _render_activity(data, args.label, args)


if __name__ == "__main__":
    main()

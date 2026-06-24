#!/usr/bin/env python3
"""Fetch Garmin Connect data and print a formatted report for AI trainer analysis.

Usage:
    python export.py
"""

from __future__ import annotations

import os
import sys
from datetime import date, timedelta
from typing import Any

sys.stdout.reconfigure(encoding="utf-8")

from config import Settings
from client import GarminClient
from formatting import (
    fmt,
    fmt_int,
    format_date_ru,
    format_pace_from_distance,
    interpret_body_battery,
    interpret_hrv,
    interpret_rhr,
)
from models import ActivitySummary, DailyMetrics


def build_daily_metrics_section(client: GarminClient, start: date, days: int) -> list[str]:
    """Build the daily health metrics section of the report."""
    lines: list[str] = ["--- DAILY METRICS ---", ""]

    for offset in range(days + 1):
        target = start + timedelta(days=offset)
        try:
            m = client.get_daily_metrics(target)
            lines.append(_format_daily_line(target, m))
        except Exception as exc:
            lines.append(f"{format_date_ru(target)} | [Error: {exc}]")

    return lines


def _format_daily_line(target_date: date, m: DailyMetrics) -> str:
    """Format a single daily metrics line."""
    rhr_str = str(m.rhr) if m.rhr is not None else "---"
    hrv_str = fmt(m.hrv_ms)
    sleep_str = f"{m.sleep_total_h}h" if m.sleep_total_h is not None else "---"
    deep_str = f"{m.sleep_deep_h}h" if m.sleep_deep_h is not None else "---"
    bb_str = f"{m.body_battery_charge}->{m.body_battery_drain}" if m.body_battery_charge is not None else "---"

    return (
        f"{format_date_ru(target_date)} | "
        f"RHR: {rhr_str} {interpret_rhr(m.rhr)} | "
        f"HRV: {hrv_str}ms ({interpret_hrv(m.hrv_ms)}) | "
        f"WakeBB: {m.body_battery_wake or '---'}{interpret_body_battery(m.body_battery_wake)} | "
        f"Sleep: {sleep_str} (deep:{deep_str}) | "
        f"Stress: {m.stress or '---'} | "
        f"BB: {bb_str} | "
        f"Steps: {m.steps or '---'}"
    )


def build_activities_section(activities: list[ActivitySummary]) -> list[str]:
    """Build the activities section of the report."""
    lines: list[str] = ["--- ACTIVITIES ---", ""]

    if not activities:
        lines.append("  No activities for the period.")
        return lines

    for idx, act in enumerate(activities, 1):
        distance_km = round(act.distance_m / 1000, 2)
        pace = format_pace_from_distance(act.duration_s, act.distance_m)

        lines.append(
            f"{idx}. {act.activity_type} | {act.start_time[:16]} | "
            f"{distance_km}km | {act.duration_s / 60:.0f}min | {pace}"
        )

        lines.append(
            f"   HR: {act.avg_hr or '---'}/{act.max_hr or '---'} | "
            f"Cadence: {fmt_int(act.avg_cadence)} | "
            f"Vert: {fmt(act.vert_osc_cm)}cm | "
            f"Contact: {fmt_int(act.ground_contact_ms)}ms"
        )

        if act.elevation_gain_m:
            lines.append(
                f"   Gain: +{round(act.elevation_gain_m)}m | "
                f"kCal: {act.calories or '---'} | TE: {fmt(act.training_effect)}"
            )

        zone_parts = []
        for zone_idx in range(1, 6):
            zone_time = act.hr_zones.get(f"Z{zone_idx}")
            if zone_time and act.duration_s:
                pct = (zone_time / act.duration_s) * 100
                zone_parts.append(f"Z{zone_idx} {pct:.0f}%")
        if zone_parts:
            lines.append(f"   Zones: {' | '.join(zone_parts)}")

        lines.append("")

    return lines


def build_report(client: GarminClient, start: date, today: date, days: int) -> str:
    """Build the full Garmin data report."""
    header = f"GARMIN DATA SYNC: {start.strftime('%d.%m.%Y')} - {today.strftime('%d.%m.%Y')}"
    report_lines = ["=" * 60, header, "=" * 60, ""]

    report_lines.extend(build_daily_metrics_section(client, start, days))
    report_lines.append("")

    try:
        activities = client.get_recent_activities(days)
    except Exception:
        activities = []

    report_lines.extend(build_activities_section(activities))
    report_lines.append("=" * 60)

    return "\n".join(report_lines)


def main() -> None:
    """Entry point: authenticate, fetch data, print report."""
    settings = Settings()
    quiet = settings.QUIET

    def log(message: str) -> None:
        if not quiet:
            print(message, file=sys.stderr)

    today = date.today()
    start_date = today - timedelta(days=settings.DAYS)

    log("[1/3] Authenticating with Garmin Connect...")
    client = GarminClient.from_env(log_fn=log)

    log("[2/3] Loading daily metrics...")
    log("[3/3] Loading activities...")

    report = build_report(client, start_date, today, settings.DAYS)
    print(report)


if __name__ == "__main__":
    main()

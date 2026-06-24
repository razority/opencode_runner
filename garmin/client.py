"""Thin Garmin Connect client wrapper.

Handles API calls only. Authentication is delegated to GarminAuth.
Returns structured dataclasses from models.py.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from typing import Any, Callable

from garminconnect import Garmin

from auth import GarminAuth
from models import ActivitySummary, DailyMetrics, LapData, TelemetryPoint


# Mapping from Garmin API metric keys to our model field names.
_TELEMETRY_KEYS: dict[str, str] = {
    "directTimestamp": "timestamp_ms",
    "directHeartRate": "hr_bpm",
    "directSpeed": "speed_mps",
    "directGradeAdjustedSpeed": "gap_mps",
    "directRunCadence": "cadence_spm",
    "directStrideLength": "stride_cm",
    "directVerticalOscillation": "vert_osc_cm",
    "directGroundContactTime": "ground_contact_ms",
    "directVerticalRatio": "vert_ratio",
    "directElevation": "elevation_m",
    "directPower": "power_w",
    "directBodyBattery": "body_battery",
    "directAvailableStamina": "stamina_available",
    "directPotentialStamina": "stamina_potential",
    "directRespirationRate": "resp_rate",
    "directLatitude": "lat",
    "directLongitude": "lon",
    "directDoubleCadence": "double_cadence",
    "directVerticalSpeed": "vert_speed_mps",
    "directPerformanceCondition": "perf_condition",
    "sumDistance": "distance_m",
    "sumDuration": "duration_s",
    "sumMovingDuration": "moving_duration_s",
    "sumElapsedDuration": "elapsed_s",
    "sumAccumulatedPower": "accum_power",
}


class GarminClient:
    """Thin wrapper around the Garmin Connect API.

    Returns structured dataclasses instead of raw dicts.
    """

    def __init__(self, client: Garmin) -> None:
        self._client = client

    @classmethod
    def from_env(cls, log_fn: Callable[[str], None] = print) -> GarminClient:
        """Create and authenticate a client using .env settings."""
        auth = GarminAuth()
        raw_client = auth.login(log_fn=log_fn)
        return cls(raw_client)

    def get_daily_metrics(self, target_date: datetime) -> DailyMetrics:
        """Fetch all health metrics for a single day."""
        date_str = target_date.date().isoformat() if hasattr(target_date, "date") else str(target_date)
        stats = self._client.get_stats(date_str)
        sleep_raw = self._client.get_sleep_data(date_str)
        hrv_raw = self._client.get_hrv_data(date_str)

        sleep_dto: dict = {}
        if isinstance(sleep_raw, dict):
            sleep_dto = sleep_raw.get("dailySleepDTO", {}) or {}

        rhr = stats.get("restingHeartRate") or stats.get("lastSevenDaysAvgRestingHeartRate")
        rhr = int(rhr) if rhr is not None else None

        hrv_value = None
        if isinstance(hrv_raw, dict):
            hrv_summary = hrv_raw.get("hrvSummary") or {}
            hrv_value = hrv_summary.get("lastNightAvg") or hrv_raw.get("weeklyAvg")
        if not hrv_value:
            hrv_value = sleep_raw.get("avgOvernightHrv") if isinstance(sleep_raw, dict) else None
        hrv_value = round(float(hrv_value), 1) if hrv_value else None

        sleep_total_s = sleep_dto.get("sleepTimeSeconds") or stats.get("sleepingSeconds")
        sleep_deep_s = sleep_dto.get("deepSleepSeconds")

        return DailyMetrics(
            rhr=rhr,
            hrv_ms=hrv_value,
            sleep_total_h=round(sleep_total_s / 3600, 1) if sleep_total_s else None,
            sleep_deep_h=round(sleep_deep_s / 3600, 1) if sleep_deep_s else None,
            body_battery_wake=stats.get("bodyBatteryAtWakeTime"),
            stress=stats.get("averageStressLevel"),
            body_battery_charge=stats.get("bodyBatteryChargedValue"),
            body_battery_drain=stats.get("bodyBatteryDrainedValue"),
            steps=stats.get("totalSteps"),
        )

    def get_recent_activities(self, days: int) -> list[ActivitySummary]:
        """Fetch activities from the last N days."""
        try:
            all_activities = self._client.get_activities(0, 50)
        except Exception:
            return []

        cutoff = datetime.now() - timedelta(days=days)
        recent: list[ActivitySummary] = []

        for raw in all_activities:
            try:
                start = datetime.strptime(
                    raw.get("startTimeLocal", ""), "%Y-%m-%d %H:%M:%S"
                )
                if start < cutoff:
                    continue
            except (ValueError, TypeError):
                continue

            hr_zones = {
                f"Z{i}": round(raw.get(f"hrTimeInZone_{i}", 0) or 0, 1)
                for i in range(1, 6)
            }

            recent.append(ActivitySummary(
                activity_id=str(raw.get("activityId", "")),
                activity_type=raw.get("activityType", {}).get("typeKey", "unknown"),
                start_time=raw.get("startTimeLocal", ""),
                distance_m=raw.get("distance", 0) or 0,
                duration_s=raw.get("duration", 0) or 0,
                avg_hr=raw.get("averageHR"),
                max_hr=raw.get("maxHR"),
                avg_cadence=raw.get("averageRunningCadenceInStepsPerMinute"),
                vert_osc_cm=raw.get("avgVerticalOscillation"),
                ground_contact_ms=raw.get("avgGroundContactTime"),
                elevation_gain_m=raw.get("elevationGain", 0) or 0,
                calories=raw.get("calories"),
                training_effect=raw.get("aerobicTrainingEffect"),
                hr_zones=hr_zones,
            ))

        return recent

    def get_activity_detail(self, activity_id: str) -> dict[str, Any]:
        """Fetch raw activity summary."""
        return self._client.get_activity(activity_id)

    def get_activity_laps(self, activity_id: str) -> list[LapData]:
        """Fetch and parse activity laps."""
        raw = self._client.get_activity_splits(activity_id)
        laps: list[LapData] = []
        for lap in raw.get("lapDTOs", []):
            laps.append(LapData(
                lap_index=lap.get("lapIndex"),
                start_time=lap.get("startTimeGMT", ""),
                distance_m=round(lap.get("distance", 0), 1),
                duration_s=round(lap.get("duration", 0), 2),
                moving_duration_s=round(lap.get("movingDuration", 0), 2),
                avg_speed_mps=round(lap.get("averageSpeed", 0), 3),
                max_speed_mps=round(lap.get("maxSpeed", 0), 3),
                avg_hr=lap.get("averageHR"),
                max_hr=lap.get("maxHR"),
                avg_cadence=round(lap.get("averageRunCadence", 0), 1),
                max_cadence=lap.get("maxRunCadence"),
                elevation_gain_m=round(lap.get("elevationGain", 0), 1),
                elevation_loss_m=round(lap.get("elevationLoss", 0), 1),
                calories=lap.get("calories"),
                avg_power_w=lap.get("averagePower"),
                max_power_w=lap.get("maxPower"),
                vert_osc_cm=round(lap.get("verticalOscillation", 0), 2),
                ground_contact_ms=lap.get("groundContactTime"),
                stride_length_cm=round(lap.get("strideLength", 0), 1),
                start_lat=lap.get("startLatitude"),
                start_lon=lap.get("startLongitude"),
                end_lat=lap.get("endLatitude"),
                end_lon=lap.get("endLongitude"),
            ))
        return laps

    def get_activity_events(self, activity_id: str) -> list[dict[str, Any]]:
        """Fetch event DTOs for an activity."""
        raw = self._client.get_activity_splits(activity_id)
        return raw.get("eventDTOs", [])

    def get_activity_telemetry(self, activity_id: str) -> list[TelemetryPoint]:
        """Fetch detailed telemetry (time-series) for an activity."""
        details = self._client.get_activity_details(activity_id)
        descriptors = details.get("metricDescriptors", [])
        raw_points = details.get("activityDetailMetrics", [])

        key_index: dict[str, int] = {}
        for idx, desc in enumerate(descriptors):
            raw_key = desc.get("key", "")
            out_key = _TELEMETRY_KEYS.get(raw_key)
            if out_key:
                key_index[out_key] = idx

        points: list[TelemetryPoint] = []
        for raw_pt in raw_points:
            metrics = raw_pt.get("metrics", [])
            values: dict[str, float | None] = {}
            for field_name, idx in key_index.items():
                values[field_name] = metrics[idx] if idx < len(metrics) else None

            points.append(TelemetryPoint(
                timestamp_ms=values.get("timestamp_ms"),
                hr_bpm=values.get("hr_bpm"),
                speed_mps=values.get("speed_mps"),
                gap_mps=values.get("gap_mps"),
                cadence_spm=values.get("cadence_spm"),
                stride_cm=values.get("stride_cm"),
                vert_osc_cm=values.get("vert_osc_cm"),
                ground_contact_ms=values.get("ground_contact_ms"),
                vert_ratio=values.get("vert_ratio"),
                elevation_m=values.get("elevation_m"),
                power_w=values.get("power_w"),
                body_battery=values.get("body_battery"),
                stamina_available=values.get("stamina_available"),
                stamina_potential=values.get("stamina_potential"),
                resp_rate=values.get("resp_rate"),
                lat=values.get("lat"),
                lon=values.get("lon"),
                double_cadence=values.get("double_cadence"),
                vert_speed_mps=values.get("vert_speed_mps"),
                perf_condition=values.get("perf_condition"),
                distance_m=values.get("distance_m"),
                duration_s=values.get("duration_s"),
                moving_duration_s=values.get("moving_duration_s"),
                elapsed_s=values.get("elapsed_s"),
                accum_power=values.get("accum_power"),
            ))

        return points

    def find_activities(
        self, start: datetime, end: datetime
    ) -> list[ActivitySummary]:
        """Find activities within a date range."""
        try:
            all_activities = self._client.get_activities(0, 50)
        except Exception:
            return []

        matching: list[ActivitySummary] = []
        hr_zones_fields = {f"hrTimeInZone_{i}" for i in range(1, 6)}

        for raw in all_activities:
            try:
                act_date = datetime.strptime(
                    raw.get("startTimeLocal", ""), "%Y-%m-%d %H:%M:%S"
                )
                if not (start <= act_date <= end):
                    continue
            except (ValueError, TypeError):
                continue

            hr_zones = {
                f"Z{i}": round(raw.get(f"hrTimeInZone_{i}", 0) or 0, 1)
                for i in range(1, 6)
            }

            matching.append(ActivitySummary(
                activity_id=str(raw.get("activityId", "")),
                activity_type=raw.get("activityType", {}).get("typeKey", "unknown"),
                start_time=raw.get("startTimeLocal", ""),
                distance_m=raw.get("distance", 0) or 0,
                duration_s=raw.get("duration", 0) or 0,
                avg_hr=raw.get("averageHR"),
                max_hr=raw.get("maxHR"),
                avg_cadence=raw.get("averageRunningCadenceInStepsPerMinute"),
                vert_osc_cm=raw.get("avgVerticalOscillation"),
                ground_contact_ms=raw.get("avgGroundContactTime"),
                elevation_gain_m=raw.get("elevationGain", 0) or 0,
                calories=raw.get("calories"),
                training_effect=raw.get("aerobicTrainingEffect"),
                hr_zones=hr_zones,
            ))

        return matching

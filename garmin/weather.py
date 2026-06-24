"""Weather data service using Open-Meteo API.

Free, no API key required. Fetches hourly weather for activity GPS coordinates.
"""

from __future__ import annotations

import sys
from datetime import datetime
from typing import Any

import requests

from models import WeatherData

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

HOURLY_PARAMS = [
    "temperature_2m",
    "relative_humidity_2m",
    "apparent_temperature",
    "precipitation",
    "rain",
    "weather_code",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
]


class WeatherService:
    """Fetches and filters weather data from Open-Meteo."""

    def fetch_hourly(
        self,
        latitude: float,
        longitude: float,
        target_date: datetime,
        timezone: str = "auto",
    ) -> dict[str, Any] | None:
        """Fetch raw hourly weather for a location and date."""
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": ",".join(HOURLY_PARAMS),
            "timezone": timezone,
            "start_date": target_date.date().isoformat(),
            "end_date": target_date.date().isoformat(),
        }

        try:
            resp = requests.get(OPEN_METEO_URL, params=params, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            print(f"  [Ошибка погоды: {exc}]", file=sys.stderr)
            return None

    def get_for_activity(
        self,
        latitude: float,
        longitude: float,
        activity_start: str,
        activity_end: str | None = None,
    ) -> WeatherData | None:
        """Get weather data covering the activity time window.

        Returns a WeatherData model with hourly data filtered to activity window.
        """
        try:
            start_dt = datetime.fromisoformat(activity_start.replace("Z", "+00:00"))
        except ValueError:
            return None

        raw = self.fetch_hourly(latitude, longitude, start_dt)
        if not raw or "hourly" not in raw:
            return None

        hourly = raw["hourly"]
        times = hourly.get("time", [])

        # Determine activity hour range
        activity_start_h = start_dt.hour
        if activity_end:
            try:
                end_dt = datetime.fromisoformat(activity_end.replace("Z", "+00:00"))
                activity_end_h = end_dt.hour + 1
            except ValueError:
                activity_end_h = activity_start_h + 3
        else:
            activity_end_h = activity_start_h + 3

        # Filter to activity window (with 1-hour buffer)
        filtered_indices = [
            i for i, t in enumerate(times)
            if activity_start_h - 1 <= int(t.split("T")[1].split(":")[0]) <= activity_end_h
        ]

        filtered_hourly: dict[str, list[Any]] = {}
        for key in hourly:
            values = hourly[key]
            filtered_hourly[key] = [values[i] for i in filtered_indices if i < len(values)]

        # Compute summary
        temps = filtered_hourly.get("temperature_2m", [])
        humidity = filtered_hourly.get("relative_humidity_2m", [])
        precip = filtered_hourly.get("precipitation", [])
        wind = filtered_hourly.get("wind_speed_10m", [])
        gusts = filtered_hourly.get("wind_gusts_10m", [])

        return WeatherData(
            lat=latitude,
            lon=longitude,
            date=start_dt.date().isoformat(),
            temperature_avg=round(sum(temps) / len(temps), 1) if temps else None,
            temperature_min=min(temps) if temps else None,
            temperature_max=max(temps) if temps else None,
            humidity_avg=round(sum(humidity) / len(humidity)) if humidity else None,
            precipitation_total=round(sum(precip), 1) if precip else None,
            wind_avg_kmh=round(sum(wind) / len(wind), 1) if wind else None,
            wind_gusts_max_kmh=max(gusts) if gusts else None,
            hourly=filtered_hourly,
        )

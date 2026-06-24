"""Centralized configuration for Garmin sync tools.

Loads .env once and exposes typed settings and metric thresholds.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_ENV_PATH)


class Settings:
    """Application settings loaded from .env."""

    # Garmin credentials
    EMAIL: str = os.getenv("GARMIN_EMAIL", "")
    PASSWORD: str = os.getenv("GARMIN_PASSWORD", "")
    MFA_CODE: str | None = os.getenv("GARMIN_MFA_CODE")
    TOKEN_STORE: str = os.getenv("GARMINTOKENS", "")

    # Behavior
    DAYS: int = int(os.getenv("GARMIN_DAYS", "7"))
    QUIET: bool = os.getenv("GARMIN_QUIET", "0") == "1"
    DETAIL: bool = os.getenv("GARMIN_DETAIL", "1") == "1"

    # Login retry
    LOGIN_RETRIES: int = 3
    RETRY_BASE_DELAY_SEC: int = 30


class Thresholds:
    """Metric status thresholds (from athlete profile)."""

    # HRV (ms)
    HRV_BALANCED: float = 55
    HRV_UNBALANCED: float = 40

    # Resting heart rate
    RHR_GREEN_MAX: int = 52
    RHR_YELLOW_MAX: int = 55

    # Body battery at wake
    BB_GREEN_MIN: int = 70
    BB_YELLOW_MIN: int = 50


WEEKDAYS_RU: list[str] = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

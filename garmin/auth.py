"""Garmin Connect authentication with retry logic.

Handles login via email/password or token, with automatic retry on 429.
"""

from __future__ import annotations

import sys
import time
from typing import Callable

from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)

from config import Settings


class GarminAuth:
    """Authenticate with Garmin Connect and return an authorized client."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings()

    def login(self, log_fn: Callable[[str], None] = print) -> Garmin:
        """Login and return an authorized Garmin client.

        Tries token first, falls back to email/password.
        Retries on 429 (rate limit).

        Raises SystemExit on unrecoverable errors.
        """
        s = self._settings
        if not s.EMAIL and not s.TOKEN_STORE:
            log_fn("ERROR: Нужен GARMIN_EMAIL в .env или валидный GARMINTOKENS")
            sys.exit(1)

        prompt_mfa = (lambda: s.MFA_CODE) if s.MFA_CODE else None

        for attempt in range(1, s.LOGIN_RETRIES + 1):
            try:
                client = Garmin(s.EMAIL, s.PASSWORD, prompt_mfa=prompt_mfa)
                client.login()
                return client

            except GarminConnectTooManyRequestsError:
                if attempt < s.LOGIN_RETRIES:
                    wait = attempt * s.RETRY_BASE_DELAY_SEC
                    log_fn(f"  429 (попытка {attempt}/{s.LOGIN_RETRIES}) — жду {wait}с...")
                    time.sleep(wait)
                else:
                    log_fn("429 Too Many Requests — Garmin временно заблокировал IP.")
                    log_fn(f"Сделано {s.LOGIN_RETRIES} попыток. Подожди 10-15 минут.")
                    sys.exit(1)

            except GarminConnectAuthenticationError as exc:
                msg = str(exc)
                if "mfa" in msg.lower():
                    if s.MFA_CODE:
                        log_fn(f"MFA-код {s.MFA_CODE} не подошёл или устарел.")
                    else:
                        log_fn("Требуется MFA. Укажи GARMIN_MFA_CODE=код в .env")
                else:
                    log_fn(f"Ошибка аутентификации: {exc}")
                sys.exit(1)

            except GarminConnectConnectionError as exc:
                log_fn(f"Ошибка соединения: {exc}")
                sys.exit(1)

            except Exception as exc:
                log_fn(f"ERROR: Garmin login failed: {exc}")
                sys.exit(1)

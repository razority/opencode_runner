"""One-time script to obtain a Garmin Connect API token.

After first successful login, token is saved to TOKEN_STORE and can be
used by garminclient.py without MFA prompts.
"""

from __future__ import annotations

import os
from pathlib import Path

from garminconnect import Garmin

EMAIL = input("Email от Garmin Connect: ").strip()
PASSWORD = input("Пароль: ").strip()

has_2fa = input("У тебя включена 2FA (коды на почту/телефон)? [y/N]: ").strip().lower()

TOKEN_STORE = str(Path(__file__).parent / ".garminconnect" / "garmin_tokens.json")

try:
    garmin = Garmin(
        email=EMAIL,
        password=PASSWORD,
        prompt_mfa=lambda: input("Код 2FA из письма/СМС: ").strip() if has_2fa == "y" else "000000",
    )

    garmin.login(TOKEN_STORE)

    print(f"\n[OK] Токен сохранён: {TOKEN_STORE}")
    print("Теперь можно использовать garminclient.py без повторного входа.")

except Exception as e:
    print(f"\n[!] Ошибка: {e}")

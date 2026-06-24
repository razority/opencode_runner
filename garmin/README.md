# Garmin Sync — инструкция для ИИ-тренера

## Структура

```
garmin/
  config.py            — Settings + Thresholds (загрузка .env, константы порогов)
  auth.py              — GarminAuth (логин, retry, токены)
  models.py            — Dataclasses: DailyMetrics, ActivitySummary, LapData, TelemetryPoint, WeatherData
  client.py            — GarminClient (тонкая обёртка: get_daily_metrics, get_recent_activities, find_activities)
  weather.py           — WeatherService (Open-Meteo API)
  formatting.py        — Чистые функции: format_pace, format_date_ru, interpret_hrv/rhr/bb
  analysis.py          — analyze_per_km, calc_weather_adjustment
  export.py            — Текстовый отчёт (метрики + активности)
  inspect_activity.py  — Детальный JSON одной тренировки + погода
  format_activity.py   — Красивый вывод JSON-файла тренировки
  get_api_token.py     — Разовый скрипт для получения токена
  requirements.txt     — Зависимости Python
  README.md            — Этот файл
```

### Архитектура (SOLID)

| Модуль | Ответственность |
|---|---|
| `config.py` | Загрузка `.env` один раз, пороги метрик, константы |
| `auth.py` | Аутентификация: токен, email/password, retry на 429 |
| `models.py` | Структурированные dataclasses вместо голых dict |
| `client.py` | API-вызовы к Garmin Connect (без форматирования) |
| `weather.py` | HTTP-запросы к Open-Meteo, фильтрация по времени |
| `formatting.py` | Чистые функции без side effects |
| `analysis.py` | Вычисления: анализ по км, поправка на погоду |
| `export.py` / `inspect_activity.py` / `format_activity.py` | Тонкие скрипты, только компонуют модули |

## Как запустить

### 0. Установка окружения

```bash
# Создать виртуальное окружение
python -m venv .venv

# Активировать
.venv\Scripts\activate

# Установить зависимости
pip install -r requirements.txt
```

### 1. Получение токена (однократно)

```bash
python garmin/get_api_token.py
# Ввести email и пароль от Garmin Connect
# При 2FA — ввести код из письма
```

### 2. Текстовый отчёт

```bash
python garmin/export.py
```

### 3. Детальный JSON тренировки

```bash
python garmin/inspect_activity.py --days 3
python garmin/inspect_activity.py --date 2026-12-25
python garmin/inspect_activity.py --date 2026-12-25 --output activity.json
```

### 4. Красивый вывод JSON

```bash
python garmin/format_activity.py garmin/activity.json
python garmin/format_activity.py garmin/activity.json --raw --sample 10
```

Флаги:
- `--label` — заголовок отчёта (по умолчанию "Тренировка")
- `--per-km` — анализ по километрам (по умолчанию включён)
- `--raw` — сырой вывод телеметрии (вместо по км)
- `--sample N` — сколько точек показать в raw-режиме (по умолчанию 5)

Пример вывода (по километрам):

```
============================================================
Забег 24.06
============================================================
Дистанция:    11.00 км
Время:        51.8 мин (3106с)
Темп:         4:42/км
Средний HR:   153
Макс HR:      159
...

Лапы (1):
  L1: 11.00км 51.8мин 4:42/км HR=153-159 кад=184.9 конт=222.0мс ...

По километрам:
  км   темп    HR  макс  кад  конт   шаг  верт   BB
  ────────────────────────────────────────────────────────
    1  4:31/км  145  155  172   192  105.2   7.1   86
    2  4:26/км  153  156  195   214  116.0   7.8   84
    ...
   10  5:05/км  155  158  180   210  102.7   7.2   73
  ────────────────────────────────────────────────────────
  сред         154       185   208  110.6
```

## Что приходит

### Ежедневные метрики (export.py)

| Метрика | Источник | Описание |
|---|---|---|
| RHR | `restingHeartRate` | Пульс покоя + статус: [OK] <=52, [C] 53-55, [!] 56+ |
| HRV | `hrvSummary.lastNightAvg` | ВСР (ms) + статус: Balanced >=55, Unbalanced 40-54, Low <40 |
| WakeBB | `bodyBatteryAtWakeTime` | Body Battery при пробуждении + [G] >=70, [Y] 50-69, [R] <50 |
| Сон | `dailySleepDTO.sleepTimeSeconds` | Общий сон (часы) |
| Глубокий сон | `dailySleepDTO.deepSleepSeconds` | Глубокий сон (часы) |
| Стресс | `averageStressLevel` | Средний стресс (0-100) |
| BB | `bodyBatteryChargedValue` → `DrainedValue` | Заряд → расход Body Battery за день |
| Шаги | `totalSteps` | Суточный шагомер |

### Активности (export.py)

| Поле | Ключ в API |
|---|---|
| Тип | `activityType.typeKey` |
| Дистанция | `distance` (м) |
| Время | `duration` (сек) |
| Темп | вычисляется из distance/duration |
| Средний HR | `averageHR` |
| Макс HR | `maxHR` |
| Каденс | `averageRunningCadenceInStepsPerMinute` |
| Вертикальные колебания | `avgVerticalOscillation` (см) |
| Время контакта | `avgGroundContactTime` (мс) |
| Набор высоты | `elevationGain` (м) |
| Калории | `calories` |
| Тренировочный эффект | `aerobicTrainingEffect` |
| Зоны HR | `hrTimeInZone_1` ... `hrTimeInZone_5` (сек) |

### Детальная тренировка (inspect_activity.py)

Источники данных:
- `get_activity(id)` — summaryDTO (агрегаты)
- `get_activity_splits(id)` — лапы (интервалы, круги)
- `get_activity_details(id)` — телеметрия (~1570 точек по 26 метрик)

Структура JSON:

```json
{
  "activity_id": "23359238033",
  "activity_type": "running",
  "start_time": "2026-06-24T08:37:28.0",
  "summary": { ... },
  "hr_zones": { "Z1": ..., "Z2": ..., "Z3": ..., "Z4": ..., "Z5": ... },
  "laps": [ ... ],
  "events": [ ... ],
  "telemetry_points": 1570,
  "telemetry": [
    {
      "hr_bpm": 88.0,
      "speed_mps": 1.63,
      "gap_mps": 1.62,
      "cadence_spm": 56.0,
      "stride_cm": 87.4,
      "vert_osc_cm": 6.05,
      "ground_contact_ms": null,
      "elevation_m": 58.0,
      "power_w": 124.0,
      "body_battery": 87.0,
      "stamina_available": 98.0,
      "lat": 57.17,
      "lon": 65.56,
      ...
    },
    ...
  ]
}
```

Метрики телеметрии (26 штук):
- Пульс, темп, GAP, каденс, длина шага
- Вертикальные колебания, вертикальный рейтинг, время контакта с землёй
- Высота, GPS координаты
- Мощность, стамина (доступная/потенциальная)
- Body Battery, частота дыхания, производительность

### Погода (weather.py)

Источник: [Open-Meteo API](https://open-meteo.com) — бесплатный, без API-ключа.

Координаты берутся из GPS-старта тренировки. Данные фильтруются по временному окну активности (±1 час).

Структура в JSON:

```json
"weather": {
  "coordinates": { "lat": 57.17, "lon": 65.56 },
  "date": "2026-06-24",
  "summary": {
    "temperature_avg": 20.7,
    "temperature_min": 19.5,
    "temperature_max": 22.0,
    "humidity_avg": 83,
    "precipitation_total": 0.0,
    "wind_avg_kmh": 12.2,
    "wind_gusts_max_kmh": 29.5
  },
  "hourly": {
    "time": ["2026-06-24T07:00", "2026-06-24T08:00", ...],
    "temperature_2m": [19.5, 20.6, ...],
    "relative_humidity_2m": [89, 84, ...],
    "precipitation": [0.0, 0.0, ...],
    "wind_speed_10m": [12.5, 11.9, ...]
  }
}
```

Отключение: `--no-weather` в inspect_activity.py.

## Согласование формата отчёта

**Формат отчёта нужно согласовать.** После каждого `/garmin-sync` или `/garmin-inspect` выдавай краткий анализ:

- Какие метрики в зелёной/жёлтой/красной зоне
- Сравнение с планом тренировок: выполнено/пропущено/качество
- Рекомендации на следующие дни
- Если нужно — скорректируй формат, сохрани его в отдельный .md файл

## Настройка (.env)

| Переменная | Описание | По умолчанию |
|---|---|---|
| `GARMIN_EMAIL` | Email от Garmin Connect | нужен если нет токена |
| `GARMIN_PASSWORD` | Пароль от Garmin Connect | нужен если нет токена |
| `GARMINTOKENS` | Путь к JSON с токеном | авто (после первого входа) |
| `GARMIN_MFA_CODE` | Одноразовый код MFA | только при первом входе |
| `GARMIN_DAYS` | Сколько дней тянуть | 7 |
| `GARMIN_QUIET` | Подавить логи (0/1) | 0 |

## Флаги скриптов

### inspect_activity.py

| Флаг | Описание |
|---|---|
| `--date YYYY-MM-DD` | Дата активности |
| `--days N` | Сколько дней искать (по умолчанию 1) |
| `--output path.json` | Сохранить JSON на диск |
| `--no-weather` | Не запрашивать погоду |

### format_activity.py

| Флаг | Описание |
|---|---|
| `--label "Текст"` | Заголовок отчёта |
| `--sample N` | Кол-во точек телеметрии (по умолчанию 5) |
| `--per-km` | Анализ по километрам (по умолчанию вкл) |
| `--raw` | Показать raw-телеметрию вместо per-km |

## Токен

После первого успешного входа токен сохраняется в `garmin/.garminconnect/garmin_tokens.json`. При следующих запусках MFA не требуется. Если Garmin запрашивает MFA — уведомление на почту одноразовое, дальше работает по токену.

Структура токена:
```json
{
  "di_token": "...",
  "di_refresh_token": "...",
  "di_client_id": "GARMIN_CONNECT_MOBILE_ANDROID_DI_2025Q2"
}
```

# Настройка Garmin API

> Выполняется на Шаге 9 онбординга.
> Если у атлета нет Garmin — раздел пропускается, анализ ведётся по ручным данным.

---

## 1. Установка Python и виртуального окружения

```powershell
# Проверить версию Python
python --version

# Если не установлен — скачать с python.org (версия 3.10+)

# Создать виртуальное окружение
python -m venv .venv

# Активировать
.\.venv\Scripts\activate

# Обновить pip
python -m pip install --upgrade pip
```

## 2. Установка зависимостей

```powershell
pip install garminconnect
```

## 3. Получение API-ключа

### Garmin Connect:
1. Зарегистрироваться на https://connect.garmin.com
2. Создать приложение в Garmin Developer (если требуется OAuth)
3. При использовании `garminconnect` — достаточно email + пароля (библиотека эмулирует запросы)

### Сохранение данных:

```powershell
# Тестовый запрос
python -c "from garminconnect import Garmin; client = Garmin('email', 'password'); client.login(); print('OK')"
```

## 4. Структура данных

| Команда | Что даёт |
|---|---|
| `client.get_stats(дата)` | Ежедневные метрики (RHR, шаги, калории) |
| `client.get_sleep_data(дата)` | Сон: продолжительность, фазы |
| `client.get_hrv_data(дата)` | HRV |
| `client.get_activities(0, n)` | Список тренировок (n штук) |
| `client.get_activity(activity_id)` | Детали одной тренировки |

## 5. Формат отчёта

После синка данные оформляются по протоколу из `Анализ тренировок.md`.

## Если Garmin нет

Анализ по ручным данным:
- Дистанция, время, средний темп
- Пульс (если есть пульсометр) + зоны
- Субъективная оценка (RPE 1-10)

Точность ниже, но для базового плана достаточно.

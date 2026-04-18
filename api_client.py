import os
import time
import urllib.parse
from typing import Any, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
RETRY_BACKOFF_SEC = (1, 2, 4)


def _parse_owm_error_message(response: requests.Response) -> Optional[str]:
    try:
        data = response.json()
        if isinstance(data, dict) and "message" in data:
            return str(data["message"])
    except (ValueError, TypeError):
        pass
    return None


def request_with_retry(url: str) -> tuple[Optional[requests.Response], Optional[str], bool]:
    """
    Возвращает (response, сообщение_об_ошибке, предлагать_кэш).
    Кэш предлагают при исчерпании повторов по сети/429/5xx.
    """
    last_err: Optional[str] = None
    offer_cache = False
    for attempt in range(4):
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 401:
                extra = _parse_owm_error_message(response)
                msg = "Неверный API-ключ. Проверьте переменную API_KEY в файле .env."
                if extra:
                    msg = f"{msg} ({extra})"
                return None, msg, False
            if response.status_code == 429 or response.status_code >= 500:
                last_err = (
                    f"Сервис временно недоступен или перегружен (код {response.status_code}). "
                    "Повторите запрос позже."
                )
                offer_cache = True
                if attempt < 3:
                    time.sleep(RETRY_BACKOFF_SEC[attempt])
                    continue
                return None, last_err, offer_cache
            if response.status_code != 200:
                extra = _parse_owm_error_message(response)
                msg = f"Ошибка запроса: код {response.status_code}."
                if extra:
                    msg = f"{msg} {extra}"
                return None, msg, False
            return response, None, False
        except requests.RequestException as e:
            last_err = f"Сетевая ошибка: {e}"
            offer_cache = True
            if attempt < 3:
                time.sleep(RETRY_BACKOFF_SEC[attempt])
                continue
            return None, last_err, offer_cache
    return None, last_err or "Не удалось выполнить запрос.", offer_cache


def get_city_coordinates(
    city: str,
) -> tuple[Optional[tuple[float, float]], Optional[str], bool]:
    q = urllib.parse.quote(city.strip())
    url = f"https://api.openweathermap.org/geo/1.0/direct?q={q}&appid={API_KEY}"
    response, err, offer_cache = request_with_retry(url)
    if err:
        return None, err, offer_cache
    try:
        data: Any = response.json()
    except ValueError:
        return None, "Не удалось разобрать ответ геокодинга (некорректный JSON).", False
    if not isinstance(data, list) or len(data) == 0:
        return None, "Город не найден. Проверьте написание или попробуйте другое название.", False
    item = data[0]
    return (float(item["lat"]), float(item["lon"])), None, False


def get_weather_by_coordinates(
    latitude: float, longitude: float
) -> tuple[Optional[dict], Optional[str], bool]:
    url = (
        "https://api.openweathermap.org/data/2.5/weather"
        f"?lat={latitude}&lon={longitude}&appid={API_KEY}&units=metric&lang=ru"
    )
    response, err, offer_cache = request_with_retry(url)
    if err:
        return None, err, offer_cache
    try:
        return response.json(), None, False
    except ValueError:
        return None, "Не удалось разобрать ответ о погоде (некорректный JSON).", False

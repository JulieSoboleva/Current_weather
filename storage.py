import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

CACHE_FILE = Path(__file__).resolve().parent / "weather_cache.json"
CACHE_MAX_AGE_SEC = 3 * 3600


def save_cache(
    city: Optional[str], lat: float, lon: float, weather: dict[str, Any]
) -> None:
    payload = {
        "city": city,
        "lat": lat,
        "lon": lon,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "weather": weather,
    }
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except OSError as e:
        print(f"Не удалось сохранить кэш: {e}")


def load_cache() -> Optional[dict[str, Any]]:
    try:
        with open(CACHE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def cache_is_fresh(fetched_at: str) -> bool:
    try:
        raw = fetched_at.strip()
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        ts = datetime.fromisoformat(raw)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - ts).total_seconds()
        return 0 <= age < CACHE_MAX_AGE_SEC
    except (ValueError, TypeError, OSError):
        return False

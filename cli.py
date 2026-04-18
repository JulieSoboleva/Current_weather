from typing import Optional

from api_client import API_KEY, get_city_coordinates, get_weather_by_coordinates
from storage import cache_is_fresh, load_cache, save_cache


def fetch_weather(
    city: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> tuple[Optional[dict], Optional[str], bool]:
    if city:
        coords, err, offer = get_city_coordinates(city)
        if err:
            return None, err, offer
        lat, lon = coords
        w, err2, offer2 = get_weather_by_coordinates(lat, lon)
        if w:
            save_cache(city.strip(), lat, lon, w)
        return w, err2, offer2
    if latitude is not None and longitude is not None:
        w, err, offer = get_weather_by_coordinates(latitude, longitude)
        if w:
            save_cache(None, latitude, longitude, w)
        return w, err, offer
    return None, "Укажите название города или широту и долготу.", False


def format_weather_line(place_label: str, weather: dict) -> str:
    temp = weather["main"]["temp"]
    if isinstance(temp, (int, float)):
        temp_str = f"{float(temp):.1f}"
    else:
        temp_str = str(temp)
    description = weather["weather"][0]["description"]
    return f"Погода в г.{place_label}: {temp_str}°C, {description}"


def try_show_cache_after_failure(error_message: str) -> None:
    print(error_message)
    data = load_cache()
    if not data:
        return
    fetched = data.get("fetched_at")
    if not fetched or not cache_is_fresh(str(fetched)):
        return
    weather = data.get("weather")
    if not isinstance(weather, dict):
        return
    answer = input(
        "Показать последние сохранённые данные из кэша (младше 3 ч.)? [y/N]: "
    ).strip().lower()
    if answer not in ("y", "yes", "д", "да"):
        return
    city = data.get("city")
    lat, lon = data.get("lat"), data.get("lon")
    if city:
        label = str(city)
    else:
        label = weather.get("name") or (
            f"{float(lat):.4f}, {float(lon):.4f}"
            if lat is not None and lon is not None
            else "неизвестно"
        )
    try:
        print(format_weather_line(label, weather))
    except (KeyError, TypeError, ValueError):
        print("В кэше сохранены неполные данные, вывести погоду не удалось.")


def run_cli() -> None:
    if not API_KEY or not str(API_KEY).strip():
        print("Не задан API-ключ. Создайте файл .env и укажите в нём API_KEY=ваш_ключ.")
        return
    while True:
        print("\nРежим: 1 — по городу, 2 — по координатам, 0 — выход")
        choice = input("Выберите режим: ").strip()
        if choice == "0":
            print("Выход.")
            break
        if choice == "1":
            city_input = input("Введите название города: ").strip()
            if not city_input:
                print("Название города не может быть пустым.")
                continue
            weather, err, offer_cache = fetch_weather(city=city_input)
            if weather:
                print(format_weather_line(city_input, weather))
            elif err:
                if offer_cache:
                    try_show_cache_after_failure(err)
                else:
                    print(err)
            continue
        if choice == "2":
            lat_s = input("Широта: ").strip().replace(",", ".")
            lon_s = input("Долгота: ").strip().replace(",", ".")
            try:
                lat_f = float(lat_s)
                lon_f = float(lon_s)
            except ValueError:
                print("Некорректные координаты. Ожидаются числа.")
                continue
            weather, err, offer_cache = fetch_weather(latitude=lat_f, longitude=lon_f)
            if weather:
                place = weather.get("name") or f"{lat_f:.4f}, {lon_f:.4f}"
                print(format_weather_line(str(place), weather))
            elif err:
                if offer_cache:
                    try_show_cache_after_failure(err)
                else:
                    print(err)
            continue
        print("Неверный выбор. Введите 1, 2 или 0.")


def main() -> None:
    try:
        run_cli()
    except KeyboardInterrupt:
        print("\nПрервано пользователем.")
    except Exception as e:
        print(f"Произошла непредвиденная ошибка: {e}")


if __name__ == "__main__":
    main()

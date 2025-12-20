import os
import json
import re
from typing import Dict, Optional, Tuple

from Source import response
from Source.database.requests import add_new_address
from Source.utils import build_address_from_components


def _load_env(path: str = ".env") -> None:
    """Простейшая загрузка переменных из .env в os.environ."""
    if not os.path.exists(path):
        return

    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
    except OSError:
        # Если .env не читается — просто игнорируем
        return


_load_env()


CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")

try:
    from dadata import Dadata
except ModuleNotFoundError:  # pragma: no cover
    Dadata = None


def _make_dadata_client():
    """Создаём клиента DaData, если есть токен/секрет и библиотека."""
    token = os.getenv("DADATA_TOKEN", "").strip()
    secret = os.getenv("DADATA_SECRET", "").strip()

    if not (Dadata and token and secret):
        # Нет токена/секрета или не установлена библиотека — просто не используем DaData
        return None

    return Dadata(token, secret)


_client = _make_dadata_client()


def _contains_cyrillic(text: str) -> bool:
    return bool(CYRILLIC_RE.search(text))


def _clean_with_dadata(address: str) -> Optional[Dict]:
    """Обёртка над Dadata.clean: возвращает словарь или None при ошибке."""
    if _client is None:
        # Нормализация отключена — нет токена/библиотеки
        return None

    try:
        return _client.clean("address", address)
    except Exception as exc:  # noqa: BLE001
        print(f"[Dadata] Не удалось нормализовать адрес: {exc}")
        return None



def _build_normalized_string(cleaned: Dict) -> Optional[str]:
    """Строит строку адреса из результата Dadata.

    Если в ответе нет нужных полей, возвращает None.
    """
    if not isinstance(cleaned, dict) or not cleaned:
        print("Dadata вернула пустой результат")
        return None

    pieces = []
    for key in ("street", "house", "city", "region", "country"):
        value = cleaned.get(key)
        if value:
            pieces.append(value)

    if not pieces:
        print("Не удалось собрать адрес из ответа Dadata")
        return None

    return " ".join(pieces)


def _normalize_free_text(free_text: str) -> Optional[str]:
    raw = f"{free_text} Россия"
    cleaned = _clean_with_dadata(raw)
    if not cleaned:
        return None
    return _build_normalized_string(cleaned)


def sanitize_input(text: str) -> Optional[str]:
    """убираем пробелы и др символы"""
    normalized = text.encode("utf-8", errors="ignore").decode("utf-8").strip()
    return normalized or None


def _try_parse_coordinates(text: str) -> Optional[Tuple[float, float]]:
    cleaned = text.replace(",", " ")
    parts = [p for p in cleaned.split() if p]

    if len(parts) != 2:
        return None

    try:
        lat = float(parts[0])
        lon = float(parts[1])
    except ValueError:
        return None

    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None

    return lat, lon


async def handle_free_query(free_text: str) -> None:
    raw = sanitize_input(free_text)
    if not raw:
        print("Пустой запрос. Введите адрес или координаты.")
        return

    # сначала координаты
    coords = _try_parse_coordinates(raw)
    if coords is not None:
        lat, lon = coords
        await response.send_request(f"{lat} {lon}")
        return

    # не кирилица – некорректно
    if not _contains_cyrillic(raw):
        print(
            "Некорректный ввод. "
            "Введите адрес на русском языке "
            "или две координаты через пробел/запятую."
            )
        return

    # только одно слово или меньше 5 символов
    words = [w for w in re.split(r"[,\s]+", raw) if w]
    if len(words) < 2 or len(raw) < 5:
        print(
            "Слишком короткий адрес. "
            "Уточните, например: 'Город, улица дом'."
            )
        return

    normalized = _normalize_free_text(raw)
    if not normalized:
        print(
            "Не удалось распознать адрес. "
            "Попробуйте формат: 'Город, улица дом'."
            )
        return

    await response.send_request(normalized)


async def parse_output_address(
        input_address: str, output_address: Dict) -> None:
    if not output_address:
        print("Пустой ответ от сервера геокодирования")
        return

    address_meta = output_address.get("address") or {}
    latitude = output_address.get("lat")
    longitude = output_address.get("lon")

    region = address_meta.get("state") or address_meta.get("region")
    city = (
        address_meta.get("city")
        or address_meta.get("town")
        or address_meta.get("village")
        or address_meta.get("municipality")
    )
    street = (
        address_meta.get("road")
        or address_meta.get("pedestrian")
        or address_meta.get("footway")
    )
    house = address_meta.get("house_number") or address_meta.get("building")
    postcode = address_meta.get("postcode")

    if street and house:
        street_house = f"{street} {house}"
    elif street:
        street_house = street
    else:
        street_house = house

    if not all((latitude, longitude)):
        print("Ответ сервиса не содержит координат")
        return

    country = (address_meta.get("country") or "").lower()
    full_without_coords_parts = [
        p for p in [region, city, street_house, postcode] if p]
    full_without_coords = ", ".join(full_without_coords_parts)

    if country and "россия" not in country:
        print("Адрес находится вне пределов России")
        return
    if not country and (
        "россия" not in (
            output_address.get("display_name")
            or "")
            ):
        print("Адрес находится вне пределов России")
        return

    # Сохранение в БД
    try:
        await add_new_address(
            input_address, full_without_coords, latitude, longitude)
    except Exception as exc:
        print(f"[БД] Не удалось сохранить адрес: {exc}")

    formatted_parts = (
        full_without_coords_parts + [str(latitude), str(longitude)]
    )
    formatted = ", ".join(formatted_parts)

    print(f"Полный адрес: {formatted}")

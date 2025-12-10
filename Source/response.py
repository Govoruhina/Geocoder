import json
from typing import Optional

import requests

from Source import parsing
from Source.database.requests import return_address_if_exist
from Source.utils import DEFAULT_HEADERS, NOMINATIM_URL


def _print_json_result(query: str, full_address: str, latitude: float, longitude: float) -> None:
    """JSON результат"""
    payload = {
        "query": query,
        "latitude": float(latitude),
        "longitude": float(longitude),
        "full_address": full_address,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=4))


async def send_request(address: str) -> None:
    cached = await return_address_if_exist(address)
    if cached is not None:
        _print_json_result(address, cached.full_address, cached.latitude, cached.longitude)
        return

    params = {
        "q": address,
        "format": "json",
        "limit": 1,
        "accept-language": "ru",
        "addressdetails": 1,
    }

    try:
        response = requests.get(NOMINATIM_URL, params=params, headers=DEFAULT_HEADERS, timeout=10)
    except Exception as exc: 
        print(f"Ошибка при обращении к сервису геокодирования: {exc}")
        return

    if not response.ok:
        print(f"Сервис геокодирования вернул ошибку: HTTP {response.status_code}")
        return

    try:
        payload = response.json()
    except ValueError:
        print("Не удалось разобрать ответ сервера как JSON")
        return

    if not payload:
        print("По заданному запросу ничего не найдено")
        return

    await parsing.parse_output_address(address, payload[0])

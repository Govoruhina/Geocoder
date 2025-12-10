from typing import Dict, Iterable, List, Optional

NOMINATIM_URL: str = "https://nominatim.openstreetmap.org/search"
DEFAULT_HEADERS = {
    "User-Agent": "CustomRussianGeocoder/1.0 (educational project)",
}


def _first_non_empty(mapping: Dict[str, str], keys: Iterable[str]) -> Optional[str]:
    for key in keys:
        value = mapping.get(key)
        if value:
            return value
    return None


def build_address_from_components(address_obj: Dict[str, str], include: Optional[List[str]] = None) -> Optional[str]:

    if not address_obj:
        return None

    city = _first_non_empty(
        address_obj,
        include or ("city", "town", "village", "municipality"),
    )
    road = _first_non_empty(address_obj, ("road", "pedestrian", "footway"))
    house = _first_non_empty(address_obj, ("house_number", "building"))
    region = _first_non_empty(address_obj, ("state", "region"))
    postcode = address_obj.get("postcode")
    country = address_obj.get("country")

    parts: List[str] = []

    if house and road:
        parts.append(f"{house} {road}")
    elif road:
        parts.append(road)

    if city:
        parts.append(city)

    if region:
        parts.append(region)
    if postcode:
        parts.append(postcode)
    if country:
        parts.append(country)

    return "; ".join(parts) if parts else None

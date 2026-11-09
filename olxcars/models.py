"""Normalize a raw OLX search item into a flat dict an agent can reason over."""

from __future__ import annotations

import re
from typing import Any

ITEM_URL = "https://www.olx.in/item/{id}/"

TRANSMISSION = {"1": "automatic", "2": "manual"}
OWNER = {"1": "first", "2": "second", "3": "third", "4": "fourth_plus"}

_MAIN_INFO = re.compile(r"(\d{4})\s*[-–]\s*([\d,]+)\s*km", re.I)


def _int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    try:
        return int(str(value).replace(",", "").strip())
    except ValueError:
        return None


def _parse_main_info(main_info: str) -> tuple[int | None, int | None]:
    """'2016 - 39,000 km' -> (2016, 39000)."""
    match = _MAIN_INFO.search(main_info or "")
    if not match:
        return None, None
    return int(match.group(1)), int(match.group(2).replace(",", ""))


def normalize(item: dict) -> dict:
    attrs = {p.get("key"): p for p in item.get("parameters") or [] if p.get("key")}

    def val(key: str):
        return (attrs.get(key) or {}).get("value")

    def name(key: str):
        return (attrs.get(key) or {}).get("value_name")

    price = (item.get("price") or {}).get("value") or {}
    resolved = item.get("locations_resolved") or {}
    points = item.get("locations") or []

    year = _int(val("year"))
    km = _int(val("mileage"))
    if year is None or km is None:
        parsed_year, parsed_km = _parse_main_info(item.get("main_info") or "")
        year = year if year is not None else parsed_year
        km = km if km is not None else parsed_km

    item_id = str(item.get("id") or "")
    point = points[0] if points else {}

    return {
        "id": item_id,
        "title": item.get("title"),
        "price": _int(price.get("raw")),
        "price_display": price.get("display"),
        "make": name("make"),
        "model": name("model"),
        "variant": name("variant"),
        "year": year,
        "km": km,
        "fuel": val("petrol"),
        "transmission": TRANSMISSION.get(str(val("transmission"))),
        "owner": OWNER.get(str(val("first_owner"))),
        "body": item.get("car_body_type"),
        "city": resolved.get("ADMIN_LEVEL_3_name"),
        "state": resolved.get("ADMIN_LEVEL_1_name"),
        "lat": point.get("lat"),
        "lon": point.get("lon"),
        "seller": "dealer" if (item.get("is_business") or item.get("elite_seller")) else "individual",
        "seller_name": item.get("user_name"),
        "posted": (item.get("created_at") or "")[:10],
        "images": [i.get("url") for i in item.get("images") or [] if i.get("url")],
        "url": ITEM_URL.format(id=item_id),
        "description": (item.get("description") or "").strip() or None,
    }

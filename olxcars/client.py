"""OLX India client.

Every OLX URL and query-parameter name lives in this module on purpose: the
search API is undocumented, so when OLX changes it, this is the only file that
has to change.

Transport note: OLX fingerprints the TLS ClientHello. Plain ``requests``/
``curl``/headless Chrome get connection-reset or ERR_HTTP2_PROTOCOL_ERROR.
``curl_cffi`` with a Chrome impersonation is the only client that gets through.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from curl_cffi import requests

from .models import normalize

SEARCH_URL = "https://api.olx.in/relevance/v4/search"
LOCATIONS_URL = "https://www.olx.in/api/locations"
ITEM_URL = "https://www.olx.in/item/{id}/"

INDIA_LOCATION = "1000001"
CARS_CATEGORY = "84"
PAGE_SIZE = 20  # server caps a page at 20 ads whatever limit you send

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-IN,en;q=0.9",
    "Referer": "https://www.olx.in/cars_c84/",
}

CACHE_DIR = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "olxcars"
LOCATIONS_TTL = 7 * 24 * 3600

# friendly filter name -> OLX query-parameter name
PARAM_MAP = {
    "min_price": "price_min",
    "max_price": "price_max",
    "year_min": "year_min",
    "year_max": "year_max",
    "min_km": "mileage_min",
    "max_km": "mileage_max",
    "fuel": "petrol",
    "transmission": "transmission",
    "owner": "first_owner",
    "make": "make",
    "model": "model",
    "sort": "sorting",
}

# friendly value -> OLX value, for the filters whose values are coded
VALUE_MAP = {
    "fuel": {
        "petrol": "petrol", "diesel": "diesel", "lpg": "lpg",
        "cng": "cng", "electric": "electric",
    },
    "transmission": {"manual": "2", "automatic": "1", "auto": "1"},
    "owner": {
        "first": "1", "second": "2", "third": "3",
        "fourth": "4", "fourth_plus": "4", "4+": "4",
    },
    "sort": {
        "price_asc": "asc-price", "price_desc": "desc-price",
        "newest": "desc-creation", "oldest": "asc-creation",
    },
}


class OlxError(RuntimeError):
    """An OLX request failed."""


def _balance(text: str, start: int) -> int:
    """Index just past the JSON object whose '{' is at *start*."""
    depth = 0
    in_string = False
    escaped = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i + 1
    raise OlxError("unterminated JSON object in page state")


def _extract_object(text: str, key: str) -> dict:
    """Pull ``{"key": {...}}`` out of a JS state blob and json-decode it."""
    needle = key + ":"
    idx = text.find(needle)
    if idx < 0:
        raise OlxError(f"page state has no '{key}' block")
    brace = text.find("{", idx + len(needle))
    if brace < 0:
        raise OlxError(f"page state '{key}' is not an object")
    return json.loads(text[brace:_balance(text, brace)])


class OlxClient:
    def __init__(self, impersonate: str = "chrome"):
        self.session = requests.Session(impersonate=impersonate)
        self.last_url: str | None = None

    # -- transport ---------------------------------------------------------

    def _fetch(self, url: str, params: dict | None = None, as_json: bool = True,
               tries: int = 3) -> Any:
        last = "unknown error"
        for attempt in range(tries):
            try:
                response = self.session.get(
                    url, params=params, headers=HEADERS, timeout=30
                )
                self.last_url = str(response.url)
                if response.status_code == 429 or response.status_code >= 500:
                    last = f"HTTP {response.status_code}"
                elif response.status_code >= 400:
                    raise OlxError(f"OLX returned HTTP {response.status_code} for {url}")
                return response.json() if as_json else response.text
            except OlxError:
                raise
            except Exception as exc:  # network / TLS / JSON errors
                last = f"{type(exc).__name__}: {exc}"
            time.sleep(1 + attempt * 2)
        raise OlxError(f"OLX request failed after {tries} attempts: {last}")

    # -- search ------------------------------------------------------------

    def search(self, query: str | None = None, location: str = INDIA_LOCATION,
               category: str = CARS_CATEGORY, page: int = 1,
               limit: int = PAGE_SIZE, **filters: Any) -> dict:
        params: dict[str, Any] = {
            "clientId": "pwa",
            "location": str(location),
            "category": str(category),
            "page": page,
            "limit": limit,
        }
        if query:
            params["query"] = query
        for name, value in filters.items():
            if value is None:
                continue
            key = PARAM_MAP.get(name, name)
            params[key] = VALUE_MAP.get(name, {}).get(str(value).lower(), value)

        payload = self._fetch(SEARCH_URL, params)
        metadata = payload.get("metadata") or {}
        return {
            "total": metadata.get("total_ads"),
            "page": page,
            "applied_filters": [f.get("id") for f in metadata.get("applied_filters") or []],
            "applied_sorting": (metadata.get("applied_sorting") or {}).get("key"),
            "cars": [normalize(item) for item in payload.get("data") or []],
        }

    # -- locations ---------------------------------------------------------

    def locations(self, refresh: bool = False) -> list[dict]:
        cache = CACHE_DIR / "locations.json"
        if not refresh and cache.exists() and (time.time() - cache.stat().st_mtime) < LOCATIONS_TTL:
            return json.loads(cache.read_text(encoding="utf-8"))["tree"]
        payload = self._fetch(
            LOCATIONS_URL,
            {"categoryid": CARS_CATEGORY, "location": INDIA_LOCATION, "limit": 60},
        )
        tree = payload.get("data") or []
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        tmp = cache.with_suffix(".tmp")
        tmp.write_text(json.dumps({"fetched": time.time(), "tree": tree}), encoding="utf-8")
        tmp.replace(cache)
        return tree

    def resolve_city(self, name: str, state: str | None = None) -> list[dict]:
        """Cities matching *name* (exact first, then contains), optionally in *state*."""
        wanted = name.strip().lower()
        state_wanted = state.strip().lower() if state else None
        exact: list[dict] = []
        loose: list[dict] = []
        for node, parent in _walk_tree(self.locations()):
            if node.get("type") != "CITY":
                continue
            label = (node.get("name") or "").lower()
            if wanted and wanted not in label:
                continue
            state_name = (parent.get("name") if parent else "") or ""
            if state_wanted and state_wanted not in state_name.lower():
                continue
            entry = {
                "id": str(node.get("id")),
                "name": node.get("name"),
                "state": state_name,
                "type": node.get("type"),
            }
            (exact if label == wanted else loose).append(entry)
        return exact + loose

    # -- single listing ----------------------------------------------------

    def listing(self, item_id: str) -> dict:
        html = self._fetch(ITEM_URL.format(id=item_id), as_json=False)
        states = _extract_object(html, "states")
        items = (states.get("items") or {}).get("elements") or {}
        item = items.get(str(item_id))
        if not item:
            raise OlxError(f"listing {item_id} not found on OLX (expired or wrong id)")
        car = normalize(item)
        if not car.get("city"):
            # the item page has no locations_resolved, only ids
            car.update(self._location_names(item))
        return car

    def _location_names(self, item: dict) -> dict:
        point = (item.get("locations") or [{}])[0]
        names = {str(node.get("id")): node.get("name")
                 for node, _ in _walk_tree(self.locations())}
        return {
            "city": names.get(str(point.get("city_id"))),
            "state": names.get(str(point.get("region_id"))),
        }


def _walk_tree(tree: list[dict], parent: dict | None = None):
    for node in tree:
        yield node, parent
        yield from _walk_tree(node.get("children") or [], node)


def search_cars(client: OlxClient, query: str | None = None, city: str | None = None,
                 state: str | None = None, page: int = 1, limit: int = PAGE_SIZE,
                 **filters: Any) -> dict:
    """Resolve the city, run the search, and return a result envelope."""
    location = INDIA_LOCATION
    location_name = "India"
    if city:
        matches = client.resolve_city(city, state)
        if not matches:
            raise OlxError(f"no city matching {city!r}" + (f" in {state!r}" if state else ""))
        location = matches[0]["id"]
        location_name = matches[0]["name"]
    result = client.search(query=query, location=location, page=page, limit=limit,
                            **filters)
    result["location"] = {"id": location, "name": location_name}
    return result

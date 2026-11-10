"""Fluent Query Builder for In-Memory Code Mode.

Allows agents and scripts to construct queries, fetch multiple pages in RAM,
filter/sort records in memory, and emit clean, token-efficient summaries.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Iterator
from .client import OlxClient, INDIA_LOCATION


class CarItem:
    """Convenient attribute wrapper around normalized car dict."""

    def __init__(self, data: dict):
        self._data = data

    def __getattr__(self, name: str) -> Any:
        if name in self._data:
            return self._data[name]
        raise AttributeError(f"'CarItem' has no attribute '{name}'")

    def __getitem__(self, key: str) -> Any:
        return self._data.get(key)

    def to_dict(self) -> dict:
        return dict(self._data)

    def compact(self) -> str:
        price = self._data.get("price_display") or f"₹ {self._data.get('price', 0):,}"
        year = self._data.get("year") or "N/A"
        title = self._data.get("title") or "Unknown"
        km = f"{self._data.get('km', 0):,} km" if self._data.get("km") else "N/A km"
        owner = f"{self._data.get('owner', 'N/A')} owner"
        city = self._data.get("city") or "N/A"
        url = self._data.get("url") or ""
        return f"{price} | {year} {title} | {km} | {owner} | {city} | {url}"

    def __repr__(self) -> str:
        return f"<CarItem {self.compact()}>"


class CarCollection:
    """A collection of CarItem objects supporting chainable in-memory filtering."""

    def __init__(self, cars: list[dict | CarItem]):
        self._items = [c if isinstance(c, CarItem) else CarItem(c) for c in cars]

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[CarItem]:
        return iter(self._items)

    def __getitem__(self, index: int | slice) -> Any:
        if isinstance(index, slice):
            return CarCollection(self._items[index])
        return self._items[index]

    def filter(self, predicate: Callable[[CarItem], bool]) -> CarCollection:
        return CarCollection([c for c in self._items if predicate(c)])

    def filter_owner(self, *owners: str) -> CarCollection:
        wanted = {o.lower() for o in owners}
        return self.filter(lambda c: str(c.owner).lower() in wanted)

    def first_owner_only(self) -> CarCollection:
        return self.filter_owner("first")

    def filter_state(self, state_name: str) -> CarCollection:
        wanted = state_name.strip().lower()
        return self.filter(lambda c: str(c.state).lower() == wanted)

    def sort_by(self, key: Callable[[CarItem], Any], reverse: bool = False) -> CarCollection:
        return CarCollection(sorted(self._items, key=key, reverse=reverse))

    def top(self, n: int = 5) -> CarCollection:
        return CarCollection(self._items[:n])

    def compact(self) -> str:
        if not self._items:
            return "No cars found matching criteria."
        return "\n".join(c.compact() for c in self._items)

    def to_dicts(self) -> list[dict]:
        return [c.to_dict() for c in self._items]

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dicts(), indent=indent)

    def __repr__(self) -> str:
        return f"<CarCollection: {len(self._items)} cars>"


class OlxQuery:
    """Fluent query builder for constructing OLX searches."""

    def __init__(self, query: str = ""):
        self._query = query
        self._city: str | None = None
        self._state: str | None = None
        self._location_id: str | None = None
        self._filters: dict[str, Any] = {}

    def query(self, text: str) -> OlxQuery:
        self._query = text
        return self

    def car(self, text: str) -> OlxQuery:
        return self.query(text)

    def city(self, name: str, state: str | None = None) -> OlxQuery:
        self._city = name
        self._state = state
        return self

    def location(self, location_id: str) -> OlxQuery:
        self._location_id = str(location_id)
        return self

    def automatic(self) -> OlxQuery:
        self._filters["transmission"] = "automatic"
        return self

    def manual(self) -> OlxQuery:
        self._filters["transmission"] = "manual"
        return self

    def petrol(self) -> OlxQuery:
        self._filters["fuel"] = "petrol"
        return self

    def diesel(self) -> OlxQuery:
        self._filters["fuel"] = "diesel"
        return self

    def cng(self) -> OlxQuery:
        self._filters["fuel"] = "cng"
        return self

    def electric(self) -> OlxQuery:
        self._filters["fuel"] = "electric"
        return self

    def under(self, max_price: int) -> OlxQuery:
        self._filters["max_price"] = int(max_price)
        return self

    def price(self, min_price: int | None = None, max_price: int | None = None) -> OlxQuery:
        if min_price is not None:
            self._filters["min_price"] = int(min_price)
        if max_price is not None:
            self._filters["max_price"] = int(max_price)
        return self

    def year(self, min_year: int | None = None, max_year: int | None = None) -> OlxQuery:
        if min_year is not None:
            self._filters["year_min"] = int(min_year)
        if max_year is not None:
            self._filters["year_max"] = int(max_year)
        return self

    def km(self, max_km: int) -> OlxQuery:
        self._filters["max_km"] = int(max_km)
        return self

    def owner(self, owner_val: str, server_side: bool = False) -> OlxQuery:
        """Filter by owner. Defaults to robust in-memory filtering due to OLX server indexing bugs."""
        if server_side:
            self._filters["owner"] = str(owner_val).lower()
        else:
            self._in_memory_owner = str(owner_val).lower()
        return self

    def first_owner(self, server_side: bool = False) -> OlxQuery:
        return self.owner("first", server_side=server_side)

    def sort(self, sort_order: str) -> OlxQuery:
        self._filters["sort"] = sort_order
        return self

    def fetch(self, pages: int = 1, client: OlxClient | None = None) -> CarCollection:
        cli = client or OlxClient()
        loc_id = self._location_id
        if not loc_id and self._city:
            resolved = cli.resolve_city(self._city, state=self._state)
            if resolved:
                loc_id = resolved[0]["id"]
            else:
                loc_id = INDIA_LOCATION
        elif not loc_id:
            loc_id = INDIA_LOCATION

        all_cars: list[dict] = []
        seen_ids: set[str] = set()

        for page_idx in range(1, max(1, pages) + 1):
            res = cli.search(
                query=self._query or None,
                location=loc_id,
                page=page_idx,
                **self._filters
            )
            cars = res.get("cars", [])
            if not cars:
                break
            for c in cars:
                cid = c.get("id")
                if cid and cid not in seen_ids:
                    seen_ids.add(cid)
                    all_cars.append(c)

        collection = CarCollection(all_cars)
        if hasattr(self, "_in_memory_owner") and self._in_memory_owner:
            collection = collection.filter_owner(self._in_memory_owner)
        return collection

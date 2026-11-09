"""MCP server exposing OLX India used-car search to AI agents (stdio transport)."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .client import PAGE_SIZE, OlxClient, OlxError, search_cars

mcp = FastMCP("olxcars")
_client = OlxClient()


@mcp.tool()
def olx_search_cars(
    query: str | None = None,
    city: str | None = None,
    state: str | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
    year_min: int | None = None,
    year_max: int | None = None,
    max_km: int | None = None,
    fuel: str | None = None,
    transmission: str | None = None,
    owner: str | None = None,
    make: str | None = None,
    model: str | None = None,
    sort: str = "newest",
    page: int = 1,
    limit: int = PAGE_SIZE,
) -> dict:
    """Search used cars on OLX India.

    Args:
        query: free text, e.g. "swift diesel" or "i20".
        city: city name, e.g. "chennai". Omit for all of India.
        state: state name, to disambiguate a city with the same name.
        min_price / max_price: price in rupees.
        year_min / year_max: model year.
        max_km: maximum kilometres driven.
        fuel: petrol | diesel | lpg | cng | electric.
        transmission: manual | automatic.
        owner: first | second | third | fourth.
        make: brand slug, e.g. "maruti-suzuki".
        model: model slug, e.g. "maruti-suzuki-swift".
        sort: price_asc | price_desc | newest | oldest.
        page: 1-based page number (20 ads per page).
        limit: ads per page (server caps at 20).
    """
    result = search_cars(
        _client, query=query, city=city, state=state, page=page, limit=limit,
        min_price=min_price, max_price=max_price, year_min=year_min,
        year_max=year_max, max_km=max_km, fuel=fuel, transmission=transmission,
        owner=owner, make=make, model=model, sort=sort,
    )
    return {
        "total": result["total"],
        "returned": len(result["cars"]),
        "location": result["location"],
        "filters_applied": result["applied_filters"],
        "sorting": result["applied_sorting"],
        "cars": result["cars"],
    }


@mcp.tool()
def olx_list_cities(query: str, state: str | None = None) -> list[dict]:
    """Resolve an Indian city name to OLX location ids.

    Args:
        query: city name fragment, e.g. "chen".
        state: optional state name to disambiguate.
    """
    return _client.resolve_city(query, state)


@mcp.tool()
def olx_get_car(car_id: str) -> dict:
    """Full detail for one OLX car listing.

    Args:
        car_id: the id from a search result, e.g. "1859748625".
    """
    try:
        return _client.listing(car_id)
    except OlxError as exc:
        return {"error": str(exc)}


def main() -> int:
    mcp.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

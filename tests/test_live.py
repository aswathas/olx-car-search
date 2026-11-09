"""Live checks against OLX. Skipped unless OLXCARS_LIVE=1 (they hit the network)."""

import asyncio
import os

import pytest

from olxcars.client import OlxClient, search_cars

pytestmark = pytest.mark.skipif(
    os.environ.get("OLXCARS_LIVE") != "1", reason="set OLXCARS_LIVE=1 to hit OLX"
)


def test_live_search_applies_filters():
    result = search_cars(OlxClient(), query="swift", city="chennai",
                         min_price=300000, max_price=600000, year_min=2018)
    assert result["total"] > 0
    assert "price" in result["applied_filters"]
    assert "year" in result["applied_filters"]
    for car in result["cars"]:
        assert 300000 <= car["price"] <= 600000
        assert car["year"] >= 2018
        assert car["city"] == "Chennai"


def test_live_listing_matches_search():
    client = OlxClient()
    result = search_cars(client, query="swift", city="chennai")
    car = client.listing(result["cars"][0]["id"])
    assert car["id"] == result["cars"][0]["id"]
    assert car["title"] == result["cars"][0]["title"]


def test_live_mcp_server_lists_and_calls_tools():
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async def run():
        params = StdioServerParameters(command="olxcars", args=["mcp"])
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                names = {tool.name for tool in tools.tools}
                assert {"olx_search_cars", "olx_list_cities", "olx_get_car"} <= names
                result = await session.call_tool(
                    "olx_search_cars",
                    {"query": "swift", "city": "chennai", "min_price": 300000,
                     "max_price": 600000, "year_min": 2018, "limit": 5},
                )
                assert result.content
                assert "Maruti" in result.content[0].text

    asyncio.run(run())

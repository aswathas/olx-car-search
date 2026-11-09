import json
from pathlib import Path

from olxcars.client import OlxClient, search_cars
from olxcars.models import normalize

FIXTURE = json.loads((Path(__file__).parent / "fixture_item.json").read_text(encoding="utf-8"))
PARAMS = {p["key"]: p["value"] for p in FIXTURE["parameters"]}

TREE = [
    {
        "id": "1000001", "name": "India", "type": "COUNTRY",
        "children": [
            {"id": "2001173", "name": "Tamil Nadu", "type": "STATE", "children": [
                {"id": "4058657", "name": "Chennai", "type": "CITY", "children": []},
                {"id": "4058658", "name": "Coimbatore", "type": "CITY", "children": []},
            ]},
            {"id": "2001163", "name": "Maharashtra", "type": "STATE", "children": [
                {"id": "4059026", "name": "Thane", "type": "CITY", "children": []},
                {"id": "4059027", "name": "Chennai", "type": "CITY", "children": []},
            ]},
        ],
    }
]


class FakeClient(OlxClient):
    """Offline client: captures outgoing params instead of hitting OLX."""

    def __init__(self):
        super().__init__()
        self.captured = None

    def _fetch(self, url, params=None, as_json=True, tries=3):
        self.captured = dict(params or {})
        return {
            "metadata": {"total_ads": 3, "applied_filters": [{"id": "category"}],
                         "applied_sorting": {"key": "desc-creation"}},
            "data": [FIXTURE],
        }

    def locations(self, refresh=False):
        return TREE


def test_normalize_extracts_fields():
    car = normalize(FIXTURE)
    assert car["id"] == FIXTURE["id"]
    assert car["price"] == int(FIXTURE["price"]["value"]["raw"])
    assert car["price_display"] == FIXTURE["price"]["value"]["display"]
    assert car["year"] == int(PARAMS["year"])
    assert car["km"] == int(PARAMS["mileage"])
    assert car["fuel"] == PARAMS["petrol"]
    assert car["transmission"] == "manual"  # parameter value "2"
    assert car["owner"] == "first"
    assert car["url"] == f"https://www.olx.in/item/{FIXTURE['id']}/"
    assert car["description"]


def test_normalize_falls_back_to_main_info():
    car = normalize(dict(FIXTURE, parameters=[]))
    year, km = FIXTURE["main_info"].replace(",", "").split(" - ")
    assert car["year"] == int(year)
    assert car["km"] == int(km.replace(" km", ""))


def test_search_maps_friendly_filters_to_olx_params():
    client = FakeClient()
    client.search(query="swift", min_price=100000, max_km=60000, fuel="diesel",
                  transmission="manual", owner="first", sort="price_asc",
                  make="maruti-suzuki")
    assert client.captured == {
        "clientId": "pwa", "location": "1000001", "category": "84",
        "page": 1, "limit": 20, "query": "swift", "price_min": 100000,
        "mileage_max": 60000, "petrol": "diesel", "transmission": "2",
        "first_owner": "1", "sorting": "asc-price", "make": "maruti-suzuki",
    }


def test_resolve_city_prefers_exact_and_honours_state():
    client = FakeClient()
    assert client.resolve_city("chennai")[0]["id"] == "4058657"
    assert client.resolve_city("chennai")[0]["state"] == "Tamil Nadu"
    matches = client.resolve_city("chennai", state="maharashtra")
    assert [m["id"] for m in matches] == ["4059027"]


def test_search_cars_passes_location_and_filters():
    client = FakeClient()
    result = search_cars(client, query="swift", city="chennai", min_price=300000,
                         sort="price_asc")
    assert client.captured["location"] == "4058657"
    assert client.captured["price_min"] == 300000
    assert client.captured["sorting"] == "asc-price"
    assert result["total"] == 3
    assert result["location"]["name"] == "Chennai"
    assert result["cars"][0]["id"] == FIXTURE["id"]

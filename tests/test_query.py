from unittest.mock import MagicMock
from olxcars.query import OlxQuery, CarCollection, CarItem


def test_car_item_attributes_and_compact():
    data = {
        "id": "12345",
        "title": "Hyundai i10 Sportz",
        "price": 350000,
        "price_display": "₹ 3,50,000",
        "year": 2014,
        "km": 45000,
        "fuel": "petrol",
        "transmission": "automatic",
        "owner": "first",
        "city": "Chennai",
        "state": "Tamil Nadu",
        "url": "https://www.olx.in/item/12345/",
    }
    car = CarItem(data)
    assert car.id == "12345"
    assert car.price == 350000
    assert car.owner == "first"
    compact = car.compact()
    assert "₹ 3,50,000" in compact
    assert "Hyundai i10 Sportz" in compact
    assert "first owner" in compact
    assert "Chennai" in compact


def test_car_collection_filtering_and_sorting():
    cars = [
        {"id": "1", "price": 400000, "km": 60000, "owner": "first", "state": "Tamil Nadu"},
        {"id": "2", "price": 300000, "km": 80000, "owner": "second", "state": "Tamil Nadu"},
        {"id": "3", "price": 250000, "km": 30000, "owner": "first", "state": "Kerala"},
    ]
    col = CarCollection(cars)
    assert len(col) == 3

    # filter owner
    firsts = col.first_owner_only()
    assert len(firsts) == 2
    assert [c.id for c in firsts] == ["1", "3"]

    # filter state
    tn_only = col.filter_state("Tamil Nadu")
    assert len(tn_only) == 2
    assert [c.id for c in tn_only] == ["1", "2"]

    # sorting by km
    sorted_km = col.sort_by(lambda c: c.km)
    assert [c.id for c in sorted_km] == ["3", "1", "2"]

    # top n
    top1 = col.top(1)
    assert len(top1) == 1
    assert top1[0].id == "1"


def test_olx_query_builder_params():
    q = (
        OlxQuery("i10")
        .city("Chennai", state="Tamil Nadu")
        .automatic()
        .under(400000)
        .first_owner()
        .petrol()
    )
    assert q._query == "i10"
    assert q._city == "Chennai"
    assert q._state == "Tamil Nadu"
    assert q._filters["transmission"] == "automatic"
    assert q._filters["max_price"] == 400000
    assert q._filters["owner"] == "first"
    assert q._filters["fuel"] == "petrol"


def test_olx_query_fetch_with_mock_client():
    mock_client = MagicMock()
    mock_client.resolve_city.return_value = [{"id": "4059162", "name": "Chennai"}]
    mock_client.search.side_effect = [
        {
            "cars": [
                {"id": "c1", "title": "Car 1", "price": 300000, "owner": "first"},
                {"id": "c2", "title": "Car 2", "price": 350000, "owner": "second"},
            ]
        },
        {
            "cars": [
                {"id": "c3", "title": "Car 3", "price": 280000, "owner": "first"},
            ]
        },
    ]

    q = OlxQuery("i10").city("Chennai").automatic().under(400000)
    col = q.fetch(pages=2, client=mock_client)

    assert len(col) == 3
    assert mock_client.search.call_count == 2
    mock_client.resolve_city.assert_called_once_with("Chennai", state=None)
    assert [c.id for c in col] == ["c1", "c2", "c3"]

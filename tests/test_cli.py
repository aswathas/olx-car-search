import pytest
from unittest.mock import patch
from olxcars.cli import main


def test_cli_run_eval_math(capsys):
    ret = main(["run", "2 + 2"])
    assert ret == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == "4"


def test_cli_run_query_mocked(capsys):
    with patch("olxcars.query.OlxClient") as MockClient:
        instance = MockClient.return_value
        instance.resolve_city.return_value = [{"id": "4059162", "name": "Chennai"}]
        instance.search.return_value = {
            "cars": [
                {
                    "id": "1",
                    "title": "Hyundai i10",
                    "price_display": "₹ 3,50,000",
                    "year": 2014,
                    "km": 40000,
                    "owner": "first",
                    "city": "Chennai",
                    "url": "https://www.olx.in/item/1/",
                }
            ]
        }

        ret = main(["run", "OlxQuery('i10').city('chennai').fetch(pages=1).top(1)"])
        assert ret == 0
        captured = capsys.readouterr()
        assert "₹ 3,50,000" in captured.out
        assert "Hyundai i10" in captured.out

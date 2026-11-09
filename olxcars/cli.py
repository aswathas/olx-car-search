"""olxcars — search OLX India used cars from a terminal."""

from __future__ import annotations

import argparse
import json
import sys

from .client import PAGE_SIZE, OlxClient, OlxError, search_cars


def _add_search_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("query", nargs="?", help="free text, e.g. 'swift diesel'")
    parser.add_argument("--city", help="city name, e.g. chennai")
    parser.add_argument("--state", help="state name, to disambiguate a city")
    parser.add_argument("--min-price", type=int)
    parser.add_argument("--max-price", type=int)
    parser.add_argument("--year-min", type=int)
    parser.add_argument("--year-max", type=int)
    parser.add_argument("--min-km", type=int)
    parser.add_argument("--max-km", type=int)
    parser.add_argument("--fuel", choices=["petrol", "diesel", "lpg", "cng", "electric"])
    parser.add_argument("--transmission", choices=["manual", "automatic"])
    parser.add_argument("--owner", choices=["first", "second", "third", "fourth"])
    parser.add_argument("--make", help="brand slug, e.g. maruti-suzuki")
    parser.add_argument("--model", help="model slug, e.g. maruti-suzuki-swift")
    parser.add_argument("--sort", choices=["price_asc", "price_desc", "newest", "oldest"],
                        default="newest")
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--limit", type=int, default=PAGE_SIZE)


def _print_table(cars: list[dict]) -> None:
    for car in cars:
        bits = [
            f"{car['price_display'] or car['price']}",
            str(car.get("year") or "?"),
            f"{car['km']:,} km" if car.get("km") is not None else "? km",
            " ".join(str(car.get(k)) for k in ("make", "model") if car.get(k)),
            car.get("fuel") or "",
            car.get("transmission") or "",
            f"[{car.get('city') or '?'}, {car.get('state') or '?'}]",
            car.get("url") or "",
        ]
        print(" | ".join(b for b in bits if b))


def cmd_search(args: argparse.Namespace) -> int:
    client = OlxClient()
    result = search_cars(
        client,
        query=args.query,
        city=args.city,
        state=args.state,
        page=args.page,
        limit=args.limit,
        min_price=args.min_price,
        max_price=args.max_price,
        year_min=args.year_min,
        year_max=args.year_max,
        min_km=args.min_km,
        max_km=args.max_km,
        fuel=args.fuel,
        transmission=args.transmission,
        owner=args.owner,
        make=args.make,
        model=args.model,
        sort=args.sort,
    )
    if args.debug:
        print(f"# GET {client.last_url}", file=sys.stderr)
        print(f"# applied_filters={result['applied_filters']} "
              f"sorting={result['applied_sorting']}", file=sys.stderr)
    cars = result["cars"]
    if args.table:
        _print_table(cars)
    else:
        print(json.dumps({
            "total": result["total"],
            "returned": len(cars),
            "location": result["location"],
            "filters_applied": result["applied_filters"],
            "sorting": result["applied_sorting"],
            "cars": cars,
        }, indent=2, ensure_ascii=False))
    return 0


def cmd_cities(args: argparse.Namespace) -> int:
    client = OlxClient()
    matches = client.resolve_city(args.query, args.state)
    if not matches:
        print(f"no city matching {args.query!r}", file=sys.stderr)
        return 2
    print(json.dumps(matches, indent=2, ensure_ascii=False))
    return 0


def cmd_listing(args: argparse.Namespace) -> int:
    client = OlxClient()
    print(json.dumps(client.listing(args.item_id), indent=2, ensure_ascii=False))
    return 0


def cmd_mcp(args: argparse.Namespace) -> int:
    from .mcp_server import main as mcp_main

    return mcp_main()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="olxcars", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    search = sub.add_parser("search", help="search used cars")
    _add_search_args(search)
    search.add_argument("--table", action="store_true", help="human-readable output")
    search.add_argument("--debug", action="store_true", help="show the request URL on stderr")
    search.set_defaults(func=cmd_search)

    cities = sub.add_parser("cities", help="resolve a city name to an OLX location id")
    cities.add_argument("query")
    cities.add_argument("--state")
    cities.set_defaults(func=cmd_cities)

    listing = sub.add_parser("listing", help="full detail for one ad id")
    listing.add_argument("item_id")
    listing.set_defaults(func=cmd_listing)

    mcp = sub.add_parser("mcp", help="run the MCP server on stdio")
    mcp.set_defaults(func=cmd_mcp)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except OlxError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())

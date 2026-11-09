# SPEC — `olxcars`: OLX India used-car search CLI + MCP server

Status: **awaiting approval**. No implementation code until approved.

## Problem

Buying a used car on OLX India means clicking through a web UI that cannot express
"in Chennai, 2018-2021, under ₹6L, under 40k km, manual, first owner". An AI agent
cannot click through OLX either. There is no public OLX API.

Goal: one tool that returns structured, filterable used-car listings from OLX India,
callable both from a terminal and from an AI agent over MCP.

## Verified facts (research, 2026-11-09)

Everything below was probed live against OLX from this machine.

### Transport — the load-bearing detail

Plain HTTP clients are blocked at the TLS layer:

| Client | Result against `www.olx.in` |
|---|---|
| `curl` (default, http/2) | `ERR_HTTP2_PROTOCOL_ERROR` in Chrome; `curl` → timeout, then connection reset |
| `requests` (Python) | `ConnectionResetError` / read timeout |
| Headless Chrome (agent-browser) | `net::ERR_HTTP2_PROTOCOL_ERROR` |
| **`curl_cffi` + `impersonate='chrome'`** | **HTTP 200, clean JSON** |

OLX (CloudFront + Cloudflare) fingerprints the TLS ClientHello. `curl_cffi` reproduces
a real Chrome handshake; everything else gets dropped. `curl_cffi` is a hard dependency —
not a nice-to-have.

### Search endpoint

```
GET https://api.olx.in/relevance/v4/search
GET https://www.olx.in/api/relevance/v4/search     # same handler
```

Query parameters (all verified working — wrong names are silently ignored, so the
applied-filter echo in the response is the correctness check):

| Param | Meaning | Verified example |
|---|---|---|
| `clientId` | `pwa` | required in practice |
| `category` | category id | `84` = Cars |
| `location` | location id | `1000001` = India, `<city_id>` = city |
| `query` | free text | `swift` → 15 950 hits vs 1.9 M unfiltered |
| `page` | 1-based page | `page=2` returns a different first item |
| `limit` | page size | server caps at 20 ads/page regardless of `limit=50` |
| `make` / `model` | slugs | `make=maruti-suzuki` → 14 739 |
| `price_min` / `price_max` | rupees | `price_min=100000` → applied filter `price` |
| `year_min` / `year_max` | year | `year_min=2018` → 5 887 |
| `mileage_min` / `mileage_max` | km | `mileage_max=60000` → 4 626 |
| `first_owner` | 1=First 2=Second 3=Third 4=Fourth+ | `first_owner=1` → 7 926 |
| `transmission` | 1=Automatic 2=Manual | verified applied |
| `petrol` | `petrol`\|`diesel`\|`lpg` | `petrol=petrol` → 8 432 |
| `inspected` | `true` | verified applied |
| `sorting` | `asc-price`\|`desc-price`\|`desc-creation` | `sorting=asc-price` → applied_sorting `asc-price` |

Unknown params are ignored, not rejected — so the tool must echo
`metadata.applied_filters` in `--debug` output rather than trusting its own input.

### Response shape

`data[]` items carry: `id`, `title`, `price.value.raw` (int rupees) and
`price.value.display` (`₹ 4,30,000`), `main_info` (`"2016 - 39,000 km"`),
`parameters[]` (typed attrs: `make`, `model`, `variant`, `year`, `petrol`,
`transmission`, `mileage`, `first_owner`), `images[]`, `locations[].lat/lon`,
`locations_resolved` (city/state names), `user_name`, `is_business`, `elite_seller`,
`created_at`, `description`.

`metadata` carries `total_ads`, `applied_filters`, `applied_sorting`, and the full
facet list (`filters[]` with ids `category, location, make, model, price, year,
first_owner, inspected, mileage, petrol, transmission`) — usable for `--explain`.

### Locations

```
GET https://www.olx.in/api/locations?categoryid=84&location=1000001&limit=60
```
→ full tree India → state → city with ids (e.g. Delhi `4058659`). 671 KB response —
cache it locally, never fetch per search.

### Item URL

`https://www.olx.in/item/<id>/` → HTTP 200. No slug needed.

## Design

```
olx-car-search/
├── SPEC.md
├── README.md
├── pyproject.toml
├── olxcars/
│   ├── __init__.py
│   ├── client.py     # curl_cffi session, retry, search(), locations(), resolve_city()
│   ├── models.py     # raw API item → normalized car dict
│   ├── cli.py        # argparse CLI
│   └── mcp_server.py # FastMCP stdio server
└── tests/
    ├── fixture_item.json
    └── test_models.py
```

### Core: `client.py`

- One `curl_cffi.requests.Session(impersonate='chrome')`, reused across calls.
- `search(**filters) -> {total, page, items, applied_filters}`.
- `locations(refresh=False)` → cached JSON tree at `~/.cache/olxcars/locations.json`,
  7-day TTL, atomic write.
- `resolve_city(name)` → walks the tree, case-insensitive match on city (then state),
  returns id + name. Ambiguous → returns all matches so the CLI can list them.
- Retry: up to 3 attempts on connection error / 429 / 5xx with 1s, 3s backoff.

### Normalization: `models.py`

API item → flat dict the agent can reason over:

```json
{
  "id": "1859980729",
  "title": "Maruti Suzuki Swift VXi 1.2 ABS BS-IV, 2016, Petrol",
  "price": 430000,
  "price_display": "₹ 4,30,000",
  "make": "Maruti Suzuki", "model": "Swift", "variant": "VXI",
  "year": 2016, "km": 39000,
  "fuel": "petrol", "transmission": "manual", "owner": "First",
  "city": "Thane", "state": "Maharashtra",
  "lat": 19.259, "lon": 72.984,
  "seller": "dealer", "seller_name": "Hitesh vasaikar",
  "posted": "2026-10-26",
  "images": ["https://..."],
  "url": "https://www.olx.in/item/1859980729/",
  "description": "..."
}
```

`transmission` map: `1`→`automatic`, `2`→`manual`. `owner`: `1`→`first`,
`2`→`second`, `3`→`third`, else `4+`. Year/km prefer `parameters[]`, fall back to
parsing `main_info`.

### CLI: `olxcars`

```
olxcars search "swift" --city chennai --min-price 300000 --max-price 600000 \
    --year-min 2018 --year-max 2021 --max-km 40000 --fuel petrol \
    --transmission manual --owner first --make maruti-suzuki \
    --sort price_asc --page 1 --limit 20 [--json|--table] [--debug]

olxcars cities chennai          # resolve a city name -> id (shows ambiguity)
olxcars listing 1859980729     # one ad, full detail
olxcars mcp                     # run the MCP server on stdio
```

Defaults: JSON to stdout (agent-friendly). `--table` for humans (no dependency —
fixed-width text). `--debug` prints the outgoing URL and the response's
`applied_filters` so a silently-ignored filter is visible.

City matching accepts a city name (case-insensitive, contains). `--state maharashtra`
selects within a state. Unknown city → error listing near matches, exit 2.

### MCP server: `olxcars mcp`

FastMCP stdio server, three tools:

| Tool | Args | Returns |
|---|---|---|
| `olx_search_cars` | `query`, `city`, `state`, `min_price`, `max_price`, `year_min`, `year_max`, `max_km`, `fuel`, `transmission`, `owner`, `make`, `model`, `sort`, `page`, `limit` | `{total, returned, filters_applied, cars[]}` |
| `olx_list_cities` | `query` | `[{id, name, state, type}]` |
| `olx_get_car` | `id` | one car dict |

Registration for Claude Code:

```
claude mcp add olxcars -- python -m olxcars.mcp_server
```

### Tests

Offline test over a checked-in fixture: normalization of a raw API item → exact
expected dict. No network in tests. Plus one live smoke test behind `--live` that
asserts `total_ads > 0` and the applied-filter echo contains the category filter.

## Non-goals

- No price-history tracking, no watchlists, no alerts (v1 is search + read).
- No multi-country OLX.
- No login/seller contact, no image download.
- No web UI.

## Risks

1. **Undocumented internal API.** OLX can change or block it without notice.
   Mitigation: one module owns every URL/param (`client.py`), params are named
   constants, and the tool prints the applied-filter echo with `--debug` so a
   silently-dropped filter is immediately visible. If OLX changes the contract,
   only `client.py` changes.
2. **TLS fingerprinting may tighten.** `curl_cffi`'s Chrome impersonation tracks
   current Chrome; if OLX starts rejecting it, the fallback is a proxy or a
   paid scraping API. Not solvable in-repo.
3. **Crawler load.** One page fetch per search, 20 ads per page, default 1 page.
   Cached location tree. No aggressive polling.
4. **Rate limiting.** Retries with backoff; on sustained 429 the tool errors out
   rather than hammering.

## Acceptance

1. `olxcars search "swift" --city chennai --min-price 300000 --max-price 600000 --year-min 2018`
   returns only cars, only Chennai, only ₹3–6L, only 2018+, and prints the
   applied-filter echo proving each filter landed.
2. `olxcars cities chennai` resolves to a city id and lists it.
3. `olxcars listing <id>` returns the same car the search returned, with a working URL.
4. `olxcars mcp` starts and lists all three tools; a client can search through it.
5. `pytest` passes offline.

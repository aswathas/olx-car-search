---
name: aswath-olx-car-search
description: Use when building or debugging anything that queries OLX India (olx.in) listings — used cars, any category — from Python, a CLI, or an MCP server, including TLS-fingerprint blocks, category ids, filter parameter names, or location resolution.
---

# OLX India listing access

OLX India has no public API. These are the facts you need, all verified live on
2026-11-09 against `www.olx.in` / `api.olx.in`.

## The TLS wall comes first

Every ordinary HTTP client is dropped at the TLS layer:

- `curl` / `requests` / headless Chrome → `ERR_HTTP2_PROTOCOL_ERROR`, connection
  reset, or a read timeout.
- `curl_cffi` with `impersonate='chrome'` → HTTP 200.

```python
from curl_cffi import requests
r = requests.get(url, headers=HEADERS, impersonate='chrome', timeout=30)
```

Do not waste time on proxies, UA strings, or retry loops before trying
`curl_cffi` — the block is on the ClientHello, not the request.

## Endpoints

```
GET https://api.olx.in/relevance/v4/search      # search + filters
GET https://www.olx.in/api/locations?categoryid=84&location=1000001&limit=60
GET https://www.olx.in/item/<id>/               # one ad
```

`www.olx.in` and `api.olx.in` both serve the search handler.

## Search params

Wrong param names are **silently ignored**, never rejected. The only correctness
check is `metadata.applied_filters` in the response — always surface it.

| Param | Value |
|---|---|
| `clientId` | `pwa` |
| `category` | `84` = Cars |
| `location` | `1000001` = India, else a city id |
| `query` | free text |
| `page` | 1-based; `offset` is ignored |
| `limit` | server caps the page at 20 ads whatever you pass |
| `make` / `model` | slugs (`maruti-suzuki`) |
| `price_min` / `price_max` | rupees |
| `year_min` / `year_max` | year |
| `mileage_min` / `mileage_max` | km |
| `first_owner` | 1 First, 2 Second, 3 Third, 4 Fourth+ |
| `transmission` | 1 Automatic, 2 Manual |
| `petrol` | `petrol` \| `diesel` \| `lpg` |
| `inspected` | `true` |
| `sorting` | `asc-price`, `desc-price`, `desc-creation` |

`sort=`, `sort_by=`, `order=` do nothing. The param is `sorting`.

## Response

`data[]` items: `id`, `title`, `price.value.raw` (int rupees),
`price.value.display`, `main_info` (`"2016 - 39,000 km"`), `parameters[]`
(typed attrs: `make`, `model`, `variant`, `year`, `petrol`, `transmission`,
`mileage`, `first_owner`), `images[]`, `locations[].lat/lon`,
`locations_resolved` (city/state names), `user_name`, `is_business`,
`elite_seller`, `created_at`, `description`.

`metadata`: `total_ads`, `applied_filters`, `applied_sorting`, and `filters[]`
with the full facet list and counts — use it to show the user what is available.

## Locations

`/api/locations` returns the whole tree (India → state → city) with ids —
Chennai, Delhi `4058659`, etc. It is ~670 KB, so cache it
(`~/.cache/olxcars/locations.json`) instead of fetching per search.

## Item URL

`https://www.olx.in/item/<id>/` resolves without a slug.

## Mistakes to avoid

- Reaching for `requests`/`curl` first — they are blocked; use `curl_cffi`.
- Guessing filter param names. Use the table; verify via `applied_filters`.
- Expecting `limit=50` to return 50. The cap is 20 ads per page.
- Fetching `/api/locations` on every search.
- Building the slug for an item URL — the bare id path works.

## Reference implementation

`C:\Users\aswat\olx-car-search` — `olxcars/client.py` owns every URL and param
name, `olxcars/models.py` normalizes items, `olxcars/cli.py` is the CLI,
`olxcars/mcp_server.py` is the MCP server. Spec in `SPEC.md`.

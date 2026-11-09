# olxcars

Search used cars on **OLX India** from a terminal, or plug it into an AI agent over MCP.

OLX has no public API. This tool talks to OLX's own search endpoint with a Chrome
TLS fingerprint — plain `curl`/`requests` get connection-reset by OLX's edge.

## Install

```bash
pip install -e .
```

Needs Python 3.10+. Dependencies: `curl_cffi` (transport) and `mcp` (server).

From GitHub, without cloning:

```bash
pip install "olxcars @ git+https://github.com/aswathas/olx-car-search"
```

### As a Claude Code plugin

The repo is a plugin marketplace. One command installs the CLI, the MCP server
and the `aswath-olx-car-search` skill:

```bash
claude plugin marketplace add aswathas/olx-car-search
claude plugin install olxcars@olx-car-search
```

The plugin runs the MCP server through `uvx`, so no Python environment is
needed on the host.


## CLI

```bash
olxcars search "swift" --city chennai --min-price 300000 --max-price 600000 \
    --year-min 2018 --year-max 2021 --max-km 40000 --fuel petrol \
    --transmission manual --owner first --sort price_asc --table

olxcars search "i20" --city bengaluru --max-price 800000 --json
olxcars cities chennai            # resolve a city name to an OLX location id
olxcars listing 1859805530        # full detail for one ad
olxcars mcp                       # run the MCP server on stdio
```

`search` prints JSON by default (agent-friendly); `--table` prints one line per car.
`--debug` prints the outgoing request URL and OLX's own `applied_filters` echo on
stderr — use it to confirm a filter actually landed (OLX ignores unknown params
silently).

| Flag | Meaning |
|---|---|
| `--city`, `--state` | location filter; city is matched case-insensitively, `--state` disambiguates |
| `--min-price`, `--max-price` | rupees |
| `--year-min`, `--year-max` | model year |
| `--min-km`, `--max-km` | kilometres driven |
| `--fuel` | `petrol` `diesel` `lpg` `cng` `electric` |
| `--transmission` | `manual` `automatic` |
| `--owner` | `first` `second` `third` `fourth` |
| `--make`, `--model` | OLX slugs, e.g. `maruti-suzuki`, `maruti-suzuki-swift` |
| `--sort` | `price_asc` `price_desc` `newest` `oldest` |
| `--page`, `--limit` | paging; OLX serves 20 ads per page whatever `--limit` says |

Each car comes back as:

```json
{
  "id": "1859805530",
  "title": "Maruti Suzuki Swift LXI, 2018, Petrol",
  "price": 510000,
  "price_display": "₹ 5,10,000",
  "make": "Maruti Suzuki", "model": "Swift", "variant": "2018-2021 1.2 LXI",
  "year": 2018, "km": 61000,
  "fuel": "petrol", "transmission": "manual", "owner": "first",
  "city": "Chennai", "state": "Tamil Nadu", "lat": 13.045, "lon": 72.984,
  "seller": "individual", "posted": "2026-10-25",
  "images": ["https://..."],
  "url": "https://www.olx.in/item/1859805530/"
}
```

## MCP server (for your AI agent)

```bash
claude mcp add olxcars -- olxcars mcp
```

Or in `.mcp.json`:

```json
{ "mcpServers": { "olxcars": { "command": "olxcars", "args": ["mcp"] } } }
```

Tools exposed:

| Tool | Purpose |
|---|---|
| `olx_search_cars` | filtered search — query, city, state, price, year, km, fuel, transmission, owner, make, model, sort, paging |
| `olx_list_cities` | resolve an Indian city name to OLX location ids |
| `olx_get_car` | full detail for one ad id |

## Tests

```bash
python -m pytest              # offline: normalization, param mapping, city resolution
OLXCARS_LIVE=1 python -m pytest tests/test_live.py   # hits OLX, incl. MCP round-trip
```

## Notes and limits

- OLX's search API is **undocumented and can change or vanish without notice**. Every
  URL and parameter name lives in `olxcars/client.py`; if it breaks, that is the only
  file to change.
- OLX's own `price_asc` sort is not reliably sorted — treat `sorting` as a hint and
  sort client-side if exact ordering matters.
- One request per search; the location tree is cached for 7 days in
  `~/.cache/olxcars/locations.json`.
- Scope: OLX India, cars (category `84`). Other categories need their id from
  `metadata.filters`.

# Problem: Token Explosion in AI Car Search

## Context
When an AI agent searches for used cars on OLX India via standard JSON Tool Calling / MCP:
- OLX serves 20 ads per page (~40 KB JSON payload per page).
- If an agent searches 3 pages to find cars matching specific constraints (e.g. 1st owner, under 4 Lakhs, automatic, Chennai), it ingests **120 KB of raw JSON (~30,000+ tokens)**.
- Every multi-step check requires sequential network and conversational turns between LLM and MCP server.

## The Pain
1. **Context Bloat**: A single user prompt ("find me 3 automatic i10s under 4L") exhausts 20% to 30% of typical working context headroom.
2. **High Latency & Cost**: Paginating through 3-5 pages takes 3-5 round trips.
3. **Fragile Sorting**: MCP tools cannot anticipate every custom ranking formula (e.g. price-to-mileage ratio, multi-city deduplication).

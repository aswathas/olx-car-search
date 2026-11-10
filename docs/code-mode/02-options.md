# Options: Agent Interaction Paradigms for OLX Search

We evaluated three architectural options for agent search:

### Option 1: Standard MCP Server Tool (Status Quo)
- **Mechanism**: LLM issues structured JSON tool calls (`search_cars(query, location, ...)`).
- **Pros**: Standardized schema, works out-of-the-box in locked-down chat apps (Claude Desktop).
- **Cons**: Severe token tax (~30,000 tokens for 60 ads). Inflexible filtering.

### Option 2: Pre-defined CLI Flags
- **Mechanism**: Agent executes shell commands (`olxcars search "i10" --city chennai --table`).
- **Pros**: Low token cost with `--table` formatting (~800 tokens). Simple for single queries.
- **Cons**: Cannot perform multi-page joins, cross-city deduplication, or complex scoring without messy bash piping (`jq`, `awk`).

### Option 3: In-Memory "Code Mode" (Programmatic Execution)
- **Mechanism**: The agent writes a concise Python script using a fluent SDK (`OlxQuery` / `OlxClient`).
- **Pros**:
  - Paging, filtering, and scoring happen inside local RAM.
  - Only the final 3-5 lines of distilled markdown enter the LLM context (~150 tokens, **99.5% savings**).
  - Single conversational turn.
  - Zero external subscription (no Cloudflare dependency).
- **Cons**: Requires Python runtime access (available in all modern coding agents: Antigravity, Claude Code, OpenDevin).

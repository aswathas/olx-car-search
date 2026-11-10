32,450 tokens down to 142 tokens.

Why I added Code Mode to my MCP server, and why coding agents should bypass MCP entirely.

I built an MCP server for OLX India used cars. It worked on the first try. Then I ran a realistic prompt: find three automatic Hyundai i10s in Chennai under 4 lakh rupees, first owner.

To find three genuine matches, an agent needs to scan roughly three pages of search results.

That is where standard tool calling broke down:

- OLX returns 20 ads per page
- Each ad carries 25 attributes, coordinates, and photo links
- Three pages dumped 120 KB of raw JSON into the context window
- Token bill: 32,450 tokens
- Latency: 4.8 seconds across three conversational hops

The model burned a third of its working memory just to read 60 car descriptions and discard 57 of them.

So I implemented Code Mode. Instead of the agent calling a rigid JSON tool three times, the agent writes a three-line Python query using a fluent builder.

The execution happens in local memory:

1. It fetches three pages in RAM via curl-cffi
2. It filters out second owners and dealers in Python
3. It prints only the three winning listings to stdout

Result: 142 tokens returned to the model. 1.1 seconds. Exactly 99.5 percent less context tax.

Here is the rule I learned: MCP exists for locked chat apps with no shell access, like Claude Desktop. But if your agent has a terminal, running MCP is paying a heavy token penalty for a protocol you do not need.

Both interfaces now live in the same repository: MCP for chat apps, native Code Mode for terminal agents.

Repo on GitHub: https://github.com/aswathas/olx-car-search

Are you still dumping raw JSON payloads into your agent context?

#aiagents #python

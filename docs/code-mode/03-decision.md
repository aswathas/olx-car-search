# Decision: Adopt Native In-Memory Code Mode for OLX Cars

## Decision
We choose **Option 3 (In-Memory Code Mode)** as the primary programmatic interface for `olx-car-search`, while preserving the existing CLI for human shell use and the MCP server for locked-down chat clients.

## Architecture
1. **Fluent Query Builder (`olxcars/query.py`)**:
   Provides an expressive, chainable API:
   ```python
   from olxcars import OlxQuery

   cars = (
       OlxQuery("i10")
       .city("Chennai")
       .automatic()
       .under(400000)
       .first_owner()
       .fetch(pages=3)
   )
   print(cars.compact())
   ```
2. **In-Memory CLI Runner (`olxcars run`)**:
   Enables any agent to execute single-turn queries directly from the terminal without file management overhead.
3. **Zero Subscriptions**:
   Runs entirely on local hardware with existing dependencies (`curl_cffi`).

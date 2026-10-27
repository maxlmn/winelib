# WineLib for AI assistants (MCP)

Ask Claude, or any assistant that speaks MCP (the Model Context Protocol), about your own cellar: *what should I open
with lamb tonight from what's at home?*, *which 2019 Burgundies do I have?*, *what did I drink at Noble Rot?*, *which
Loire wines did I score above 93?*

`server.py` is a small MCP server that reads WineLib through its API: the running app, never the database. It's
**read-only**: it can't add, change or delete anything.

## What it can read

| Tool | |
|---|---|
| `search` | anything by name: wines, producers, appellations, regions, grapes, vineyards, places |
| `cellar` | the bottles you own, where they are, scores, ready or not; by words, colour, region, storage place |
| `what_to_open` | the bottles to drink soon and the ready ones, in one storage place or colour |
| `wine` | one wine in full: its vintages, critics, bottles and your tastings |
| `tastings` | your journal: date, wine, your rating and notes, where; since a date, at a place, above a rating |
| `wishlist` | the wines you'd like, with their market price and what you already have |
| `region`, `producer` | what you hold and have tasted from a region or a producer |

## Setting it up

On the computer where the assistant runs (Python 3.11 or newer):

```bash
pip install -r app/mcp_server/requirements.txt
```

It finds WineLib at `WINELIB_URL` (default `http://localhost:8000`). For WineLib on another machine, its address:
on a NAS through Tailscale, for example `https://nas.your-tailnet.ts.net`.

**Claude Desktop**: Settings › Developer › Edit Config, then add to `claude_desktop_config.json` (full paths) and
restart Claude:

```json
{
  "mcpServers": {
    "winelib": {
      "command": "python",
      "args": ["/path/to/winelib/app/mcp_server/server.py"],
      "env": { "WINELIB_URL": "http://localhost:8000" }
    }
  }
}
```

**Claude Code**:

```bash
claude mcp add winelib --env WINELIB_URL=http://localhost:8000 -- python /path/to/winelib/app/mcp_server/server.py
```

Other assistants: the same command (`python …/server.py`) as a stdio MCP server.

## Privacy

The assistant sees what the tools return (your bottles, tastings and notes) and sends it to its model provider like
the rest of the conversation. Nothing else leaves WineLib, and nothing in it can be changed through this server.

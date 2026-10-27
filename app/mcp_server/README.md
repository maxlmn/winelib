# WineLib for AI assistants (MCP)

Ask Claude, or any assistant that speaks MCP (the Model Context Protocol), about your own cellar: *what should I open
with lamb tonight from what's at home?*, *which 2019 Burgundies do I have?*, *what did I drink at Noble Rot?*, *which
Loire wines did I score above 93?*, *what's left to taste on the Noble Rot list?*

`server.py` is a small MCP server that works with WineLib through its API: the running app, never the database.
It reads, and it can **add lists** for you (*make a list of every wine I drank on 3 October at Claude's*, *…of the
wines whose note says "wow"*): it shows you the list and its entries and does nothing until you say yes. It never
changes or deletes anything; a list it made can be deleted in the app.

## What it can read

| Tool | |
|---|---|
| `search` | anything by name: wines, producers, appellations, regions, grapes, vineyards, places |
| `cellar` | the bottles you own, where they are, scores, ready or not; by words, colour, region, storage place |
| `what_to_open` | the bottles to drink soon and the ready ones, in one storage place or colour |
| `wine` | one wine in full: its vintages, critics, bottles and your tastings |
| `tastings` | your journal: date, wine, your rating and notes, where; by dates or one day, a place (a friend's home: with them), words in the notes, a rating |
| `lists`, `wishlist` | your lists and your progress on them: each entry tasted or not, owned or not, its note |
| `region`, `producer` | what you hold and have tasted from a region or a producer |
| `create_list`, `add_to_list` | **add**: a new list with its entries, or entries on one of your lists; after your yes |

Your yes comes through the assistant's own confirmation dialog when it has one (Claude Desktop, Claude Code); with
one that hasn't, the assistant shows you the preview and asks, and the tool acts only when called again with the
preview's token.

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
the rest of the conversation. Nothing else leaves WineLib, and nothing is changed through this server without your yes.

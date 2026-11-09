# WineLib's website

The home page and the manual, built with [Astro Starlight](https://starlight.astro.build) and published to GitHub
Pages by `.github/workflows/site.yml`.

```bash
npm install
npm run dev      # http://localhost:4321/winelib/
npm run build    # dist/
```

Pages written here: `src/content/docs/index.mdx` (the home page), `install.md`, `integrations.md`. The guides,
About the data, the MCP page and the screenshots are the app's own (`app/api/data/docs/`, `app/mcp_server/README.md`,
`screenshots/`), copied in by `scripts/sync.mjs` before each build: edit them there.

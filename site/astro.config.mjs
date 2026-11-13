// @ts-check
// WineLib's website: the home page and the manual (Starlight). The guides, About the data and the MCP page are the
// app's own Markdown, copied in by scripts/sync.mjs. Published to GitHub Pages: SITE_URL and BASE_PATH set where
// (https://maxlmn.github.io + /winelib by default; a custom domain: SITE_URL=https://example.org BASE_PATH=/).
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

const site = process.env.SITE_URL || 'https://maxlmn.github.io'; // || : an unset repository variable is ''
const base = process.env.BASE_PATH || '/winelib';

export default defineConfig({
	site,
	base,
	integrations: [
		starlight({
			title: 'WineLib',
			description: 'Your wine cellar and tasting journal, on maps. Self-hosted, open source.',
			// the app's mark (app/web/scripts/brand.mjs draws it): the same on a light or a dark page
			logo: { src: './src/assets/logo.svg', alt: '' },
			favicon: '/favicon.svg',
			head: [{ tag: 'link', attrs: { rel: 'apple-touch-icon', href: `${base.replace(/\/$/, '')}/apple-touch-icon.png` } }],
			social: [{ icon: 'github', label: 'GitHub', href: 'https://github.com/maxlmn/winelib' }],
			customCss: ['./src/styles/site.css'],
			components: { Footer: './src/components/Footer.astro' },
			lastUpdated: false,
			sidebar: [
				{ label: 'Start', items: ['install', 'guide/first-steps', 'upkeep'] },
				{
					label: 'Guides',
					items: ['guide/cellar', 'guide/tastings', 'guide/maps', 'guide/drawing', 'guide/grapes', 'guide/imports']
				},
				{ label: 'More', items: ['mcp', 'integrations', 'about/data'] }
			]
		})
	]
});

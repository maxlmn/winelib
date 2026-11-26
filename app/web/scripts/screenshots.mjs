// The README's and the website's screenshots (screenshots/*.png), retaken from a running WineLib: the demo cellar
// with the map pack installed (scripts/build_demo.py says how it's set up), each page in light and in dark.
//   node scripts/screenshots.mjs --url http://127.0.0.1:8000 --out ../../screenshots [--only home,cellar]
// Then scripts/screenshots_compose.py (the repository's) puts the phone shots in their frames, the two themes side
// by side and the walk-through's frames in a GIF.
import { chromium } from '@playwright/test';
import { mkdirSync } from 'node:fs';
import { join } from 'node:path';

const arg = (n, d) => { const i = process.argv.indexOf(`--${n}`); return i > 0 ? process.argv[i + 1] : d; };
const root = arg('url', 'http://127.0.0.1:8000').replace(/\/$/, '');
const out = arg('out', '../../screenshots');
const only = arg('only', '').split(',').filter(Boolean);
mkdirSync(out, { recursive: true });

const api = (path) => fetch(root + path).then((r) => r.json());
const first = async (q, kind) => (await api(`/api/search?q=${encodeURIComponent(q)}&limit=8`)).results.find((r) => r.kind === kind);
const settle = (page, ms = 1200) => page.waitForLoadState('networkidle').then(() => page.waitForTimeout(ms));
const top = (page, selector, offset = 12) =>
	page.locator(selector).first().evaluate((e, o) => scrollBy(0, e.getBoundingClientRect().top - o), offset);

// The demo's pages by name, so a newer demo cellar still finds them
const wine = await first('Gravières Blanc 2022', 'wine');
const rouge = await first('Gravières Rouge 2022', 'wine'); // a wine with its vineyard: the lieux-dits around it
const santenay = await first('Santenay', 'appellation');
const list = (await api('/api/lists')).find((l) => /Atlas/.test(l.name)) ?? (await api('/api/lists'))[0];
const poyeux = await first('Rougeard Les Poyeux 2010', 'wine'); // the website's background: its vineyard, the lieu-dit Les Poyeux
// the lie of the land: a steep vineyard's slope, geology, contours and shading. Its relief worked out first (as its
// page's first visit would), so the map has its contours when the picture is taken
const landonne = await first('Landonne 2019', 'wine');
const landonneVineyard = landonne && (await api(`/api/wines/${landonne.id}`)).vineyard?.id;
if (landonneVineyard) await Promise.all([api(`/api/vineyards/${landonneVineyard}/relief`), api(`/api/vineyards/${landonneVineyard}/geology`)]);
const note = (await api('/api/tastings')).tastings.find((t) => /Turque/.test(t.cuvee) && t.notes) ?? (await api('/api/tastings')).tastings.find((t) => t.notes);

/** name, the page, what to do on it before the picture; phone: the phone's size (the composed "mobile" picture);
 * hero: the website's background (its map alone, wide, a JPEG) */
const SHOTS = [
	{
		name: 'hero', path: `/wines/${poyeux.id}`, wait: 3000, hero: true,
		prep: async (p) => {
			// the lieux-dits filled in, on IGN's aerial photo; the map alone, its legend kept (it names the vineyard)
			const b = p.getByRole('button', { name: /Lieux-dits/ }).first(); await b.click(); await b.click();
			await p.getByRole('button', { name: 'Satellite' }).first().click();
			await settle(p, 5000);
			await p.addStyleTag({ content: 'main, .maplibregl-ctrl { visibility: hidden !important }' });
		}
	},
	{ name: 'home', path: '/', wait: 3500 },
	{ name: 'cellar', path: '/cellar', wait: 3500 },
	{ name: 'lists', path: '/lists', wait: 3500 },
	{ name: 'list', path: `/lists/${list.id}`, wait: 3500 },
	{ name: 'worldmap', path: '/map', wait: 3000 },
	{ name: 'map', path: '/regions/Bourgogne', wait: 3000 },
	{ name: 'wine', path: `/wines/${wine.id}`, wait: 3000 },
	{
		name: 'lieux-dits', path: `/wines/${rouge.id}`, wait: 3000,
		// the lieux-dits filled in (the toggle goes outline, hidden, filled)
		prep: async (p) => { const b = p.getByRole('button', { name: /Lieux-dits/ }).first(); await b.click(); await b.click(); await settle(p, 3000); }
	},
	{
		// zoomed in on the vineyard: its contours and shading
		name: 'terroir', path: `/wines/${landonne?.id}`, wait: 3000,
		prep: async (p) => {
			// the map opens on the appellation, the vineyard a sliver on it: zoomed in around it with the wheel
			const at = { x: 1020, y: 340 };
			await p.mouse.move(at.x, at.y);
			for (let i = 0; i < 6; i++) { await p.mouse.wheel(0, -240); await p.waitForTimeout(350); }
			await settle(p, 3500);
		}
	},
	{
		name: 'draw', path: `/appellations/${santenay.id}`, wait: 2500,
		prep: async (p) => {
			await p.locator('.action-menu .more').first().click();
			await p.getByRole('menuitem', { name: /Draw its outline/ }).click();
			await p.waitForTimeout(1500);
			await p.getByRole('button', { name: 'Start from the official outline' }).click();
			await p.getByRole('button', { name: 'Satellite' }).click();
			await settle(p, 5000);
		}
	},
	{ name: 'tastings', path: '/tastings?period=all', wait: 3500 },
	{
		name: 'sticker', path: `/tastings/${note.id}`,
		prep: async (p) => { await p.getByRole('button', { name: /Share/ }).first().click(); await p.waitForTimeout(1200); }
	},
	{ name: 'summary', path: '/summary' },
	{
		name: 'grapes', path: '/grapes', wait: 2500,
		prep: async (p) => { await p.getByRole('button', { name: /Family network/ }).click(); await p.waitForTimeout(3500); await top(p, '.seg', 60).catch(() => {}); }
	},
	{ name: 'grape', path: '/grapes/Syrah', prep: (p) => top(p, '.family, .panel', 180).catch(() => {}) },
	{
		name: 'search', path: '/',
		prep: async (p) => { await p.keyboard.press('Control+k'); await p.keyboard.type('saumur'); await p.waitForTimeout(1200); }
	},
	{ name: 'winelist', path: '/cellar/list' },
	{ name: 'phone-home', path: '/', phone: true, wait: 3500 },
	{ name: 'phone-cellar', path: '/cellar', phone: true, wait: 3500 },
	{ name: 'phone-wine', path: `/wines/${wine.id}`, phone: true, wait: 3000 }
].filter((s) => !only.length || only.includes(s.name));

// WebGL through ANGLE's software renderer: Chromium's default headless one leaves a map's top blank when its foot is
// below the window (the phone's home page), a real browser draws it whole
const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
for (const dark of [false, true]) {
	for (const s of SHOTS) {
		const ctx = await browser.newContext({
			viewport: s.phone ? { width: 390, height: 800 } : s.hero ? { width: 1920, height: 1080 } : { width: 1280, height: 673 },
			deviceScaleFactor: s.phone ? 2 : s.hero ? 1 : 1.5, colorScheme: dark ? 'dark' : 'light', isMobile: !!s.phone, hasTouch: !!s.phone
		});
		const page = await ctx.newPage();
		await page.goto(root + s.path);
		await settle(page, s.wait ?? 1200);
		try {
			if (s.prep) await s.prep(page);
		} catch (e) {
			console.log(`  ${s.name}: ${String(e.message).split('\n')[0]}`);
		}
		await page.waitForTimeout(400);
		const file = join(out, `${s.name}${dark ? '-dark' : ''}.${s.hero ? 'jpg' : 'png'}`);
		// the hero: the map beside the sidebar
		await page.screenshot(s.hero ? { path: file, type: 'jpeg', quality: 82, clip: { x: 200, y: 0, width: 1720, height: 1080 } } : { path: file });
		console.log(file);
		await ctx.close();
	}
}

// The walk-through (screenshots/demo.gif): frames of a visit, each with how long it stays (clip/<theme>/NN.png and
// frames.json), put together by scripts/screenshots_compose.py
if (!only.length || only.includes('clip')) {
	for (const dark of [false, true]) {
		const dir = join(out, 'clip', dark ? 'dark' : 'light');
		mkdirSync(dir, { recursive: true });
		const ctx = await browser.newContext({ viewport: { width: 960, height: 600 }, deviceScaleFactor: 1, colorScheme: dark ? 'dark' : 'light' });
		const page = await ctx.newPage();
		const frames = [];
		const frame = async (ms) => {
			const file = `${String(frames.length).padStart(2, '0')}.png`;
			await page.screenshot({ path: join(dir, file) });
			frames.push({ file, ms });
		};
		const scroll = async (by, steps = 6) => {
			for (let i = 0; i < steps; i++) { await page.mouse.wheel(0, by / steps); await page.waitForTimeout(60); await frame(70); }
		};
		// the lists, one of them
		await page.goto(root + '/lists'); await settle(page); await frame(1600);
		await scroll(260); await frame(900);
		await page.goto(root + `/lists/${list.id}`); await settle(page); await frame(1800);
		// a search, letter by letter, to a wine
		await page.keyboard.press('Control+k'); await page.waitForTimeout(300); await frame(500);
		for (const c of 'gravieres') { await page.keyboard.type(c); await page.waitForTimeout(220); await frame(140); }
		await page.waitForTimeout(600); await frame(900);
		// the wine among what was found (a producer of that name comes first)
		const found = page.locator('[data-index]').filter({ hasText: wine.title }).first();
		await found.hover(); await page.waitForTimeout(200); await frame(900);
		await found.click(); await settle(page, 3000); await frame(2200);
		// its vineyard on the map, closer
		for (let i = 0; i < 2; i++) { await page.locator('.maplibregl-ctrl-zoom-in').first().click(); await page.waitForTimeout(900); await frame(500); }
		await frame(1400);
		// the cellar's racks
		await page.goto(root + '/cellar'); await settle(page); await frame(1200);
		await scroll(420, 8); await frame(2400);
		const { writeFileSync } = await import('node:fs');
		writeFileSync(join(dir, 'frames.json'), JSON.stringify(frames));
		console.log(`${dir}: ${frames.length} frames`);
		await ctx.close();
	}
}
await browser.close();

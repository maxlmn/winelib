// The static demo's data: opens every page of a running WineLib (a demo cellar's) in Chromium, following its links,
// and saves each answer the pages get from the API, with an index the demo build reads (src/lib/demo.ts).
//
//     node scripts/crawl-demo.mjs --url http://127.0.0.1:8124 --out ../../demo-data [--max 20000] [--tabs 6]
//
// Forms (new, edit) and Settings' Maintenance are left out: the demo saves nothing. Search can't be crawled (its
// answers depend on what's typed): /api/search/all is saved instead, cut to the pages opened, and searched in the
// browser.
import { chromium } from '@playwright/test';
import { createHash } from 'node:crypto';
import { mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const arg = (name, fallback) => {
	const i = process.argv.indexOf(`--${name}`);
	return i > 0 ? process.argv[i + 1] : fallback;
};
const root = arg('url', 'http://127.0.0.1:8124').replace(/\/$/, '');
const out = arg('out', 'demo-data');
const max = +arg('max', '20000');

/** Pages worth opening: the app's own, not its forms or the API */
const SKIP = /^\/api\/|\/(new|edit)$|^\/visits\/|^\/welcome|tab=maintenance|[?&]task=/;
const START = ['/', '/cellar', '/cellar/list', '/lists', '/tastings', '/summary', '/producers', '/grapes', '/vintages',
	'/places', '/map', '/settings', '/about', '/help'];

rmSync(out, { recursive: true, force: true });
mkdirSync(out, { recursive: true });
const index = {};
let bytes = 0;

const browser = await chromium.launch();
const tabs = +arg('tabs', '6'); // pages open at once
const record = async (res) => {
	const req = res.request();
	const url = new URL(res.url());
	if (req.method() !== 'GET' || url.origin !== root || !url.pathname.startsWith('/api/') || res.status() !== 200) return;
	const key = url.pathname + url.search;
	if (key in index) return;
	index[key] = null; // taken, while its body comes
	try {
		const body = await res.body();
		const type = (res.headers()['content-type'] ?? '').split(';')[0];
		const name = createHash('sha1').update(key).digest('hex').slice(0, 16);
		const file = type === 'application/json' ? `${name}.json` : `${name}.bin`;
		writeFileSync(join(out, file), body);
		bytes += body.length;
		index[key] = type === 'application/json' ? file : { f: file, t: type || 'application/octet-stream' };
	} catch {
		delete index[key]; // the page moved on before its body came: asked again later
	}
};

const seen = new Set(START);
const visited = new Set(); // the pages opened
const queue = [...START];
let opened = 0;
let busy = 0; // tabs on a page: the queue may still grow while any is
async function worker() {
	const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
	page.on('response', record);
	for (;;) {
		if (opened >= max) break;
		const path = queue.shift();
		if (path === undefined) {
			if (!busy) break;
			await new Promise((r) => setTimeout(r, 200));
			continue;
		}
		opened++;
		busy++;
		visited.add(path);
		try {
			await page.goto(root + path, { waitUntil: 'networkidle', timeout: 30_000 });
		} catch {
			console.warn('slow or failed:', path);
		}
		const hrefs = await page.$$eval('a[href]', (as) => as.map((a) => a.getAttribute('href'))).catch(() => []);
		for (const href of hrefs) {
			if (!href || !href.startsWith('/') || href.startsWith('//')) continue;
			const u = new URL(href, root);
			const p = u.pathname + u.search;
			if (SKIP.test(p) || seen.has(p)) continue;
			seen.add(p);
			queue.push(p);
		}
		busy--;
		if (opened % 100 === 0) console.log(`${opened} pages, ${queue.length} to go, ${Object.keys(index).length} answers`);
	}
	await page.close();
}
await Promise.all(Array.from({ length: tabs }, worker));
await browser.close();

for (const k of Object.keys(index)) if (index[k] === null) delete index[k];

// Search (⌘K): what it can find, only where the demo has the page. A region or a grape opened by its name keeps
// that name as its id (links.region and links.grape take either).
const PAGE = { region: 'regions', grape: 'grapes', producer: 'producers', wine: 'wines', place: 'places',
	appellation: 'appellations', vineyard: 'vineyards' };
const all = await (await fetch(`${root}/api/search/all`)).json();
const entries = [];
for (const e of all.entries) {
	const at = (id) => `/${PAGE[e.kind]}/${encodeURIComponent(String(id))}`;
	if (visited.has(at(e.id))) entries.push(e);
	else if ((e.kind === 'region' || e.kind === 'grape') && visited.has(at(e.title))) entries.push({ ...e, id: e.title });
}
writeFileSync(join(out, 'search.json'), JSON.stringify({ entries }));
index['/api/search/all'] = 'search.json';
console.log(`search: ${entries.length} of ${all.entries.length} entries`);
writeFileSync(join(out, 'index.json'), JSON.stringify(index));
console.log(`${opened} pages opened (${queue.length} left over --max), ${Object.keys(index).length} answers, ` +
	`${(bytes / 1e6).toFixed(1)} MB in ${out}`);

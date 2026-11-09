/** The static demo (VITE_DEMO=1 at build): no server, the API's answers saved as files by scripts/crawl-demo.mjs.
 * `demo-data/index.json` maps each GET the app made while crawled ("/api/wines/12?x=1") to its file; anything else
 * answers 404, and nothing is saved (a write answers 403). Search is answered here, from /api/search/all's saved
 * entries, as the API would (api/textsearch.py). Installed by hooks.client.ts before the app starts. */
import { base } from '#lib/base.ts';

export const DEMO = import.meta.env.VITE_DEMO === '1';

type Saved = string | { f: string; t: string }; // a JSON file, or another type's file and its content type

const json = (status: number, body: unknown) =>
	new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } });

type Entry = { kind: string; id: number | string; title: string; sub: string; region?: string; fields: string[] };

/** Lowercase without accents; hyphens and apostrophes become spaces (textsearch.fold) */
const fold = (s: string) =>
	s.normalize('NFKD').replace(/[^\x00-\x7f]/g, '').toLowerCase().replace(/[-'’]/g, ' ');

/** textsearch.matches: every word in one of the fields; 0 when the first starts with the query, 1 with a word */
function rank(q: string, fields: string[]) {
	const words = fold(q).split(/\s+/).filter(Boolean);
	const hay = fields.map(fold);
	if (!words.every((w) => hay.some((h) => h.includes(w)))) return null;
	return hay[0].startsWith(fold(q).trim()) ? 0 : words.some((w) => hay[0].startsWith(w)) ? 1 : 2;
}

/** /api/search's answer: the best `limit` of each kind, in the order the API gives them */
export function searchEntries(entries: Entry[], q: string, limit = 6) {
	if (q.trim().length < 2) return [];
	const byKind = new Map<string, { r: number; i: number; e: Entry }[]>();
	entries.forEach((e, i) => {
		const r = rank(q, e.fields);
		if (r === null) return;
		if (!byKind.has(e.kind)) byKind.set(e.kind, []);
		byKind.get(e.kind)!.push({ r, i, e });
	});
	return [...byKind.values()].flatMap((found) =>
		found
			.sort((a, b) => a.r - b.r || a.i - b.i)
			.slice(0, limit)
			.map(({ e: { fields: _, ...result } }) => result)
	);
}

export function installDemoFetch() {
	const real = window.fetch.bind(window);
	let index: Promise<Record<string, Saved>> | null = null;
	let found: Promise<Entry[]> | null = null; // what search can find
	const saved = () =>
		(index ??= real(`${base}/demo-data/index.json`).then((r): Promise<Record<string, Saved>> => (r.ok ? r.json() : Promise.resolve({}))));
	window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
		const url = new URL(input instanceof Request ? input.url : String(input), location.href);
		if (url.origin !== location.origin || !url.pathname.startsWith('/api/')) return real(input, init);
		const method = (init?.method ?? (input instanceof Request ? input.method : 'GET')).toUpperCase();
		if (method !== 'GET' && method !== 'HEAD')
			return json(403, { detail: "This is a read-only demo: nothing is saved. Install WineLib to keep your own cellar." });
		if (url.pathname === '/api/search') {
			const entries = await (found ??= saved().then(async (s) => {
				const r = s['/api/search/all'] ? await real(`${base}/demo-data/${s['/api/search/all']}`) : null;
				return r?.ok ? ((await r.json()).entries as Entry[]) : [];
			}));
			const limit = +(url.searchParams.get('limit') ?? 6) || 6;
			return json(200, { results: searchEntries(entries, url.searchParams.get('q') ?? '', limit) });
		}
		const hit = (await saved())[url.pathname + url.search];
		if (!hit) return json(404, { detail: 'Not part of the demo.' });
		const res = await real(`${base}/demo-data/${typeof hit === 'string' ? hit : hit.f}`);
		if (!res.ok) return json(404, { detail: 'Not part of the demo.' });
		return new Response(res.body, {
			status: 200,
			headers: { 'content-type': typeof hit === 'string' ? 'application/json' : hit.t }
		});
	};
}

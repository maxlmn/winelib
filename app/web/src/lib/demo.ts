/** The static demo (VITE_DEMO=1 at build): no server, the API's answers saved as files by scripts/crawl-demo.mjs.
 * `demo-data/index.json` maps each GET the app made while crawled ("/api/wines/12?x=1") to its file; anything else
 * answers 404, and nothing is saved (a write answers 403). Installed by hooks.client.ts before the app starts. */
import { base } from '#lib/base.ts';

export const DEMO = import.meta.env.VITE_DEMO === '1';

type Saved = string | { f: string; t: string }; // a JSON file, or another type's file and its content type

const json = (status: number, body: unknown) =>
	new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } });

export function installDemoFetch() {
	const real = window.fetch.bind(window);
	let index: Promise<Record<string, Saved>> | null = null;
	const saved = () =>
		(index ??= real(`${base}/demo-data/index.json`).then((r): Promise<Record<string, Saved>> => (r.ok ? r.json() : Promise.resolve({}))));
	window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
		const url = new URL(input instanceof Request ? input.url : String(input), location.href);
		if (url.origin !== location.origin || !url.pathname.startsWith('/api/')) return real(input, init);
		const method = (init?.method ?? (input instanceof Request ? input.method : 'GET')).toUpperCase();
		if (method !== 'GET' && method !== 'HEAD')
			return json(403, { detail: "This is a read-only demo: nothing is saved. Install WineLib to keep your own cellar." });
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

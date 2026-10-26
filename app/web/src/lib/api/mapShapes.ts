/** Map geometries, fetched only for what's drawn (POST /api/map/shapes) and kept by the browser.

Geometries rarely change, so they're saved in IndexedDB under the server's geo `version`: a later visit
draws them without downloading anything. Names and figures (bottles, tastings) come with each page's
index and are joined here, so they're always fresh. Big requests go out in batches, and `onprogress`
lets the map fill in as they arrive. */
import type { Feature, Geometry } from 'geojson';
import type { MapCollection, MapProps } from '#lib/types.ts';

type Kind = 'appellation' | 'vineyard';
type Shape = Geometry | null; // null: no boundary

const BATCH = 120; // shapes per request
const PARALLEL = 3;
const key = (kind: Kind, id: number) => `${kind}:${id}`;

const shapes = new Map<string, Shape>();
const inFlight = new Map<string, Promise<void>>();
let version = '';

/** The server's geo version, from an index response. A new one drops what's kept. */
export function useVersion(v: string | undefined) {
	if (!v || v === version) return;
	if (version) shapes.clear();
	version = v;
}

// --- IndexedDB (best effort: private windows or blocked storage just mean memory only) ---

let dbPromise: Promise<IDBDatabase | null> | null = null;

function openDb(): Promise<IDBDatabase | null> {
	dbPromise ??= new Promise((resolve) => {
		try {
			const req = indexedDB.open('winelib-map', 1);
			req.onupgradeneeded = () => req.result.createObjectStore('shapes');
			req.onsuccess = () => resolve(req.result);
			req.onerror = () => resolve(null);
			req.onblocked = () => resolve(null);
		} catch {
			resolve(null);
		}
	});
	return dbPromise;
}

async function readSaved(keys: string[]): Promise<Map<string, Shape>> {
	const found = new Map<string, Shape>();
	const db = await openDb();
	if (!db || !keys.length) return found;
	return new Promise((resolve) => {
		try {
			const store = db.transaction('shapes', 'readonly').objectStore('shapes');
			let left = keys.length;
			for (const k of keys) {
				const req = store.get(k);
				req.onsuccess = () => {
					const row = req.result as { v: string; g: Shape } | undefined;
					if (row && row.v === version) found.set(k, row.g);
					if (--left === 0) resolve(found);
				};
				req.onerror = () => --left === 0 && resolve(found);
			}
		} catch {
			resolve(found);
		}
	});
}

async function save(rows: [string, Shape][]) {
	const db = await openDb();
	if (!db || !rows.length) return;
	try {
		const store = db.transaction('shapes', 'readwrite').objectStore('shapes');
		for (const [k, g] of rows) store.put({ v: version, g }, k);
	} catch {
		/* quota or blocked: memory only */
	}
}

// --- Loading ---

async function fetchBatch(apps: number[], vines: number[]) {
	const res = await fetch('/api/map/shapes', {
		method: 'POST',
		headers: { 'content-type': 'application/json' },
		body: JSON.stringify({ appellations: apps, vineyards: vines })
	});
	if (!res.ok) throw new Error(`Shapes: error ${res.status}`);
	const data: { version: string; appellations: Record<string, Shape>; vineyards: Record<string, Shape> } = await res.json();
	useVersion(data.version);
	const rows: [string, Shape][] = [];
	for (const [kind, map] of [['appellation', data.appellations], ['vineyard', data.vineyards]] as const)
		for (const [id, g] of Object.entries(map)) rows.push([key(kind, +id), g]);
	for (const [k, g] of rows) shapes.set(k, g);
	void save(rows);
}

/** Makes sure these shapes are known: memory, then saved ones, then the server in batches.
 *  `onprogress` runs each time more of them become drawable. */
export async function loadShapes(appIds: number[], vineIds: number[], onprogress?: () => void) {
	const wanted = [...appIds.map((id) => key('appellation', id)), ...vineIds.map((id) => key('vineyard', id))];
	const waits = new Set(wanted.map((k) => inFlight.get(k)).filter((p) => p !== undefined));
	const todo = wanted.filter((k) => !shapes.has(k) && !inFlight.has(k));
	if (todo.length) {
		const job = (async () => {
			// Let the page paint its list first: reading big saved shapes back takes the main thread a moment
			await new Promise((r) => requestAnimationFrame(() => setTimeout(r)));
			const saved = await readSaved(todo);
			for (const [k, g] of saved) shapes.set(k, g);
			if (saved.size) onprogress?.();
			const missing = todo.filter((k) => !shapes.has(k));
			const batches: string[][] = [];
			for (let i = 0; i < missing.length; i += BATCH) batches.push(missing.slice(i, i + BATCH));
			const ids = (b: string[], kind: Kind) => b.filter((k) => k.startsWith(`${kind}:`)).map((k) => +k.slice(kind.length + 1));
			let next = 0;
			const worker = async () => {
				while (next < batches.length) {
					const b = batches[next++];
					await fetchBatch(ids(b, 'appellation'), ids(b, 'vineyard'));
					onprogress?.();
				}
			};
			await Promise.all(Array.from({ length: Math.min(PARALLEL, batches.length) }, worker));
		})().finally(() => todo.forEach((k) => inFlight.delete(k)));
		todo.forEach((k) => inFlight.set(k, job));
		waits.add(job);
	}
	await Promise.all(waits);
}

/** The drawable rows as a collection: each row's figures with its kept geometry (rows without one are left out). */
export function collection(kind: Kind, rows: Iterable<MapProps>): MapCollection {
	const features: Feature<Geometry, MapProps>[] = [];
	for (const p of rows) {
		const g = shapes.get(key(kind, p.id));
		if (g) features.push({ type: 'Feature', id: p.id, geometry: g, properties: p });
	}
	return { type: 'FeatureCollection', features, missing: [] };
}

/** Ids among these that turned out to have no boundary. */
export const withoutShape = (kind: Kind, ids: Iterable<number>) => [...ids].filter((id) => shapes.get(key(kind, id)) === null);

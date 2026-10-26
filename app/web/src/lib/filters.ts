import type { Bottle } from './types';

/** Cellar filters. They live in the URL, so any filtered view can be bookmarked or shared. */
export interface Filters {
	q: string;
	color: string[];
	region: string[];
	producer: string[];
	vintage: string[];
	appellation: string[];
	/** any of the wine's grapes */
	grape: string[];
	group: string[];
	loc: string[];
}

const LIST_KEYS = ['color', 'region', 'producer', 'vintage', 'appellation', 'grape', 'group', 'loc'] as const;
export type ListKey = (typeof LIST_KEYS)[number];

export function emptyFilters(): Filters {
	return { q: '', color: [], region: [], producer: [], vintage: [], appellation: [], grape: [], group: [], loc: [] };
}

type Params = Pick<URLSearchParams, 'get' | 'getAll' | 'toString'>;

export function fromParams(params: Params): Filters {
	const f = emptyFilters();
	f.q = params.get('q') ?? '';
	for (const k of LIST_KEYS) f[k] = params.getAll(k);
	return f;
}

export function toParams(f: Filters, base?: Params): URLSearchParams {
	const p = new URLSearchParams(base?.toString());
	p.delete('q');
	for (const k of LIST_KEYS) p.delete(k);
	if (f.q) p.set('q', f.q);
	for (const k of LIST_KEYS) for (const v of f[k]) p.append(k, v);
	return p;
}

export const activeCount = (f: Filters) => (f.q ? 1 : 0) + LIST_KEYS.reduce((n, k) => n + f[k].length, 0);

const inList = (list: string[], v: string | null) => !list.length || list.includes(v ?? '');
/** a wine is in when any of its grapes is selected */
const anyIn = (list: string[], vs: string[]) => !list.length || vs.some((v) => list.includes(v));

/** Every filter except location: the shelf map uses this so all bins stay on the map. */
export function filterWines(bottles: Bottle[], f: Filters): Bottle[] {
	const q = f.q.trim().toLowerCase();
	return bottles.filter(
		(b) =>
			(!q || [b.producer, b.cuvee, b.appellation, ...b.grapes].some((s) => s?.toLowerCase().includes(q))) &&
			inList(f.color, b.color) &&
			inList(f.region, b.region) &&
			inList(f.producer, b.producer) &&
			inList(f.vintage, b.vintage) &&
			inList(f.appellation, b.appellation) &&
			anyIn(f.grape, b.grapes)
	);
}

export function filterLocations(bottles: Bottle[], f: Filters): Bottle[] {
	return bottles.filter((b) => inList(f.group, b.location_group) && inList(f.loc, b.location));
}

/** Distinct values with bottle counts, most common first. */
export function options(bottles: Bottle[], key: keyof Bottle): { value: string; count: number }[] {
	const counts = new Map<string, number>();
	for (const b of bottles) {
		const v = b[key];
		if (v === null || v === '') continue;
		counts.set(String(v), (counts.get(String(v)) ?? 0) + b.qty);
	}
	return [...counts].map(([value, count]) => ({ value, count })).sort((a, b) => b.count - a.count || a.value.localeCompare(b.value));
}

/** Each grape with the bottles of the wines it's in, most common first. */
export function grapeOptions(bottles: Bottle[]): { value: string; count: number }[] {
	const counts = new Map<string, number>();
	for (const b of bottles) for (const g of b.grapes) counts.set(g, (counts.get(g) ?? 0) + b.qty);
	return [...counts].map(([value, count]) => ({ value, count })).sort((a, b) => b.count - a.count || a.value.localeCompare(b.value));
}

export function totals(bottles: Bottle[]) {
	let qty = 0, cost = 0, market = 0;
	for (const b of bottles) {
		qty += b.qty;
		cost += b.qty * b.price_base;
		market += b.qty * b.market_base;
	}
	return { qty, cost, market };
}

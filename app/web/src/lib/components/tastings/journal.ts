import type { Journal, Place, Tasting, Visit } from '#lib/api/tastings.ts';

/** Tasting filters. Like the cellar's, they live in the URL so any view can be bookmarked. */
export interface TastingFilters {
	q: string;
	color: string[];
	region: string[];
	producer: string[];
	appellation: string[];
	/** any of the wine's grapes */
	grape: string[];
	vintage: string[];
	loc: string[];
	wine: number | null;
	period: Period;
	from: string;
	to: string;
}

export const PERIODS = [
	{ id: 'ytd', label: 'Year to date' },
	{ id: 'all', label: 'All time' },
	{ id: '30d', label: 'Last 30 days' },
	{ id: 'custom', label: 'Custom' }
] as const;
export type Period = (typeof PERIODS)[number]['id'];

export const LIST_KEYS = ['color', 'region', 'producer', 'appellation', 'grape', 'vintage', 'loc'] as const;
export type ListKey = (typeof LIST_KEYS)[number];
const KEYS = ['q', 'wine', 'period', 'from', 'to', ...LIST_KEYS];

type Params = Pick<URLSearchParams, 'get' | 'getAll' | 'toString'>;

export function fromParams(p: Params): TastingFilters {
	const period = PERIODS.find((x) => x.id === p.get('period'))?.id ?? 'ytd';
	const f = { q: p.get('q') ?? '', wine: Number(p.get('wine')) || null, period, from: p.get('from') ?? '', to: p.get('to') ?? '' };
	return { ...f, ...(Object.fromEntries(LIST_KEYS.map((k) => [k, p.getAll(k)])) as Record<ListKey, string[]>) };
}

export function toParams(f: TastingFilters, base?: Params): URLSearchParams {
	const p = new URLSearchParams(base?.toString());
	for (const k of KEYS) p.delete(k);
	if (f.q) p.set('q', f.q);
	if (f.wine) p.set('wine', String(f.wine));
	if (f.period !== 'ytd') p.set('period', f.period);
	if (f.period === 'custom') {
		if (f.from) p.set('from', f.from);
		if (f.to) p.set('to', f.to);
	}
	for (const k of LIST_KEYS) for (const v of f[k]) p.append(k, v);
	return p;
}

export const emptyFilters = (period: Period = 'ytd'): TastingFilters => ({
	q: '', color: [], region: [], producer: [], appellation: [], grape: [], vintage: [], loc: [], wine: null, period, from: '', to: ''
});

/** Filters on the wine itself: restaurant visits have no wine, so they drop out when any is set. */
export const wineFiltered = (f: TastingFilters) =>
	!!(f.q.trim() || f.wine || f.color.length || f.region.length || f.producer.length || f.appellation.length || f.vintage.length);

export const activeCount = (f: TastingFilters) =>
	(f.q ? 1 : 0) + (f.wine ? 1 : 0) + LIST_KEYS.reduce((n, k) => n + f[k].length, 0);

export const isoDay = (d: Date) =>
	`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

/** Inclusive [from, to] ISO dates for the period, or null for all time. Open-ended, so notes
 * logged ahead of time stay visible. */
export function periodRange(f: TastingFilters, today = new Date()): [string, string] | null {
	const end = '9999-12-31';
	if (f.period === 'all') return null;
	if (f.period === '30d') return [isoDay(new Date(today.getFullYear(), today.getMonth(), today.getDate() - 30)), end];
	const ytd = `${today.getFullYear()}-01-01`;
	if (f.period === 'custom') return [f.from || ytd, f.to || end];
	return [ytd, end];
}

const inList = (list: string[], v: string | null) => !list.length || list.includes(v ?? '');
/** a wine is in when any of its grapes is selected */
const anyIn = (list: string[], vs: string[]) => !list.length || vs.some((v) => list.includes(v));
const inRange = (d: string, r: [string, string] | null) => !r || (d >= r[0] && d <= r[1]);

export function filterTastings(rows: Tasting[], f: TastingFilters): Tasting[] {
	const q = f.q.trim().toLowerCase();
	const range = periodRange(f);
	return rows.filter(
		(t) =>
			inRange(t.date, range) &&
			(!f.wine || t.wine_id === f.wine) &&
			(!q || [t.producer, t.cuvee, t.appellation, ...t.grapes, t.notes].some((s) => s?.toLowerCase().includes(q))) &&
			inList(f.color, t.color) &&
			inList(f.region, t.region) &&
			inList(f.producer, t.producer) &&
			inList(f.appellation, t.appellation) &&
			anyIn(f.grape, t.grapes) &&
			inList(f.vintage, t.vintage) &&
			inList(f.loc, t.location)
	);
}

export function filterVisits(journal: Journal, f: TastingFilters): Visit[] {
	if (wineFiltered(f)) return [];
	const range = periodRange(f);
	return journal.visits.filter((v) => inRange(v.date, range) && inList(f.loc, journal.places[v.place_id]?.name ?? null));
}

/** One card in the journal: the wines tasted on a day at a place, or a restaurant visit without wine. */
export interface Occasion {
	key: string;
	date: string;
	name: string;
	place: Place | null;
	wines: Tasting[];
	visit?: Visit;
	photo?: string;
}

export function occasions(journal: Journal, tastings: Tasting[], visits: Visit[]): Occasion[] {
	const groups = new Map<string, Occasion>();
	for (const t of tastings) {
		const key = `${t.date}|${t.location}`;
		let o = groups.get(key);
		if (!o) {
			o = { key, date: t.date, name: t.location, place: t.place_id ? (journal.places[t.place_id] ?? null) : null, wines: [] };
			groups.set(key, o);
		}
		o.wines.push(t);
	}
	const list: Occasion[] = [...groups.values()];
	for (const o of list) o.wines.sort((a, b) => (a.seq ?? 0) - (b.seq ?? 0));
	for (const v of visits) {
		const place = journal.places[v.place_id];
		list.push({ key: `visit-${v.id}`, date: v.date, name: place?.name ?? 'Unknown', place: place ?? null, wines: [], visit: v });
	}
	for (const o of list) o.photo = journal.photos[`${o.name.toLowerCase()}_${o.date}`];
	return list.sort((a, b) => b.date.localeCompare(a.date) || Number(!a.visit) - Number(!b.visit) || a.name.localeCompare(b.name));
}

export function stats(journal: Journal, tastings: Tasting[], visits: Visit[]) {
	// Stars count once per occasion (day + place), not per wine
	const starred = new Map<string, number>();
	for (const t of tastings) if (t.place_id) starred.set(`${t.date}|${t.place_id}`, journal.places[t.place_id]?.stars ?? 0);
	for (const v of visits) starred.set(`${v.date}|${v.place_id}`, journal.places[v.place_id]?.stars ?? 0);
	return {
		wines: tastings.length,
		producers: new Set(tastings.map((t) => t.producer_id)).size,
		unique: new Set(tastings.map((t) => t.wine_id)).size,
		stars: [...starred.values()].reduce((a, b) => a + b, 0)
	};
}

/** Distinct values with tasting counts, most common first. */
export function options(rows: Tasting[], key: keyof Tasting, extra: string[] = []) {
	const counts = new Map<string, number>(extra.map((v) => [v, 0]));
	for (const t of rows) {
		const v = t[key];
		if (v !== null && v !== '') counts.set(String(v), (counts.get(String(v)) ?? 0) + 1);
	}
	return [...counts].map(([value, count]) => ({ value, count })).sort((a, b) => b.count - a.count || a.value.localeCompare(b.value));
}

/** Each grape with the tastings of the wines it's in, most common first. */
export function grapeOptions(rows: Tasting[]) {
	const counts = new Map<string, number>();
	for (const t of rows) for (const g of t.grapes) counts.set(g, (counts.get(g) ?? 0) + 1);
	return [...counts].map(([value, count]) => ({ value, count })).sort((a, b) => b.count - a.count || a.value.localeCompare(b.value));
}

export { stars } from '#lib/format.ts';

export const wineName = (w: { producer: string; cuvee: string; vintage: string }) =>
	[w.producer, w.cuvee, w.vintage].filter(Boolean).join(' ');

const dayFmt = new Intl.DateTimeFormat('en-GB', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });
const monthFmt = new Intl.DateTimeFormat('en-GB', { month: 'long', year: 'numeric', timeZone: 'UTC' });

export const fmtDay = (iso: string) => dayFmt.format(new Date(`${iso}T00:00:00Z`));
export const fmtMonth = (iso: string) => monthFmt.format(new Date(`${iso.slice(0, 7)}-01T00:00:00Z`));

/** Markdown export: one section per occasion, wines in tasting order. */
export function toMarkdown(journal: Journal, tastings: Tasting[]): string {
	const cell = (v: unknown) => (v === null || v === undefined ? '' : String(v).replace(/\|/g, '\\|').replace(/\n/g, ' ').trim());
	const lines = [`# Tasting notes export — ${isoDay(new Date())}`, '', `${tastings.length} wines tasted`, ''];
	for (const o of occasions(journal, tastings, [])) {
		const meta = [o.place?.city, o.place?.stars ? '⭐'.repeat(o.place.stars) : ''].filter(Boolean);
		lines.push(`## ${o.date} — ${o.name}${meta.length ? ` (${meta.join(' · ')})` : ''}`, '');
		for (const w of o.wines) {
			const name = [w.producer, w.cuvee, w.vintage].map(cell).filter(Boolean).join(' ');
			const details = [w.appellation, w.color, w.format].map(cell).filter(Boolean).join(' · ');
			const scores = w.scores ? ` · ${cell(w.scores)}` : '';
			lines.push(`- **${name}** — ${details}${scores}`);
			if (w.notes) lines.push(`  > ${w.notes.replace(/\n/g, '\n  > ')}`);
		}
		lines.push('');
	}
	return lines.join('\n');
}

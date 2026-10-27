/** Lists (see app/api/routers/lists.py). */
import { error } from '@sveltejs/kit';
import { send } from './forms.ts';

type Fetch = typeof fetch;
export type EntryKind = 'wine' | 'cuvee' | 'producer';

/** What the tastings and the cellar say about an entry */
export interface EntryStatus {
	tasted: boolean;
	tastings: number;
	last_tasted: string | null;
	/** the vintage tasted last (a cuvée's or a producer's) */
	tasted_wine_id: number | null;
	best_rating: number | null;
	/** bottles in the cellar now */
	owned: number;
}

export interface ListEntry extends EntryStatus {
	id: number;
	kind: EntryKind;
	note: string | null;
	position: number;
	producer: { id: number; name: string } | null;
	/** the wine (that vintage) or the cuvée's wine; null for a producer */
	wine: { id: number; cuvee: string; vintage: string; color: string | null; appellation: string | null } | null;
	region: string | null;
	/** the wines that count for it (that one, its cuvée's vintages, its producer's) */
	wine_ids: number[];
}

export interface ListSummary {
	id: number;
	name: string;
	description: string | null;
	source: string | null;
	url: string | null;
	entries: number;
	tasted: number;
	owned: number;
	kinds: EntryKind[];
	/** the wishlist: the list the wine page's Wishlist button adds to */
	is_wishlist: boolean;
}

export interface ListCard extends ListSummary {
	dots: Dot[];
}

export interface ListDetail extends ListSummary {
	items: ListEntry[];
}

/** A list a wine or a producer is on, and how (its entry) */
export interface Membership extends ListSummary {
	as: EntryKind;
	item: EntryStatus & { id: number; note: string | null };
	wine: { cuvee: string; vintage: string } | null;
}

export interface ListIn {
	name: string;
	description: string | null;
	source: string | null;
	url: string | null;
}

async function getJson<T>(fetch: Fetch, url: string, what: string): Promise<T> {
	const r = await fetch(url);
	if (r.status === 404 || r.status === 422) error(404, `${what} not found`);
	if (!r.ok) error(r.status, `Couldn’t load the ${what.toLowerCase()}`);
	return r.json();
}

export const loadLists = (fetch: Fetch) => getJson<ListCard[]>(fetch, '/api/lists', 'Lists');
export const loadList = (fetch: Fetch, id: string | number) => getJson<ListDetail>(fetch, `/api/lists/${id}`, 'List');
export const listsOf = (fetch: Fetch, of: { wine_id: number } | { producer_id: number }) =>
	getJson<Membership[]>(fetch, `/api/lists-of?${new URLSearchParams(Object.entries(of).map(([k, v]) => [k, String(v)]))}`, 'Lists');

export const createList = (body: ListIn) => send<{ id: number }>('POST', '/api/lists', body);
export const editList = (id: number, body: ListIn) => send<{ id: number }>('PUT', `/api/lists/${id}`, body);
/** The wishlist's id, made on first use */
export const wishlistId = () => send<{ id: number }>('POST', '/api/lists/wishlist').then((r) => r.id);
export const deleteList = (id: number) => send<{ deleted: number }>('DELETE', `/api/lists/${id}`);
export const addEntry = (id: number, body: { kind: EntryKind; wine_id?: number; producer_id?: number; note?: string | null }) =>
	send<{ id: number; existing: boolean }>('POST', `/api/lists/${id}/items`, body);
export const editEntry = (id: number, item: number, body: { note?: string | null; position?: number }) =>
	send<{ id: number }>('PUT', `/api/lists/${id}/items/${item}`, body);
export const removeEntry = (id: number, item: number) => send<{ deleted: number }>('DELETE', `/api/lists/${id}/items/${item}`);

/** "Clos Rougeard Le Bourg 2016", "… any vintage", or the producer alone */
export function entryName(e: Pick<ListEntry, 'kind' | 'producer' | 'wine'>) {
	if (e.kind === 'producer' || !e.wine) return e.producer?.name ?? '';
	return [e.producer?.name, e.wine.cuvee, e.kind === 'wine' ? e.wine.vintage : null].filter(Boolean).join(' ');
}

export const KIND_LABEL: Record<EntryKind, string> = { wine: 'this vintage', cuvee: 'any vintage', producer: 'any of its wines' };

/** A note as it sorts: by its first number when it has one ("#7" 7, "3-1" 3.1, "2nd Growth" 2), then by its text;
 * no note last. Notes hold a list's ranks and tiers. */
export function noteKey(note: string | null): [number, number, string] {
	if (!note?.trim()) return [2, 0, ''];
	const m = note.match(/(\d+)(?:[-.](\d+))?/);
	return m ? [0, Number(m[1]) + (m[2] ? Number(`0.${m[2]}`) : 0), note.toLowerCase()] : [1, 0, note.toLowerCase()];
}

export const compareKeys = (a: [number, number, string], b: [number, number, string]) =>
	a[0] - b[0] || a[1] - b[1] || a[2].localeCompare(b[2]);

/** An entry as a bottle end in a list's mosaic */
export interface Dot {
	tasted: boolean;
	owned: boolean;
	region: string | null;
	color: string | null;
	note?: string | null;
}

export type DotOrder = 'list' | 'note' | 'tasted' | 'todo' | 'region';
export const DOT_ORDERS: [DotOrder, string][] = [
	['list', 'The list’s order'],
	['note', 'By note (ranks, tiers)'],
	['tasted', 'Tasted first'],
	['todo', 'To taste first'],
	['region', 'By region']
];

/** A mosaic sorted (stable: the list's order within each group) */
export function sortDots<T extends Dot>(dots: T[], order: DotOrder): T[] {
	const at = new Map(dots.map((d, i) => [d, i]));
	const pos = (a: T, b: T) => at.get(a)! - at.get(b)!;
	return [...dots].sort((a, b) =>
		order === 'note'
			? compareKeys(noteKey(a.note ?? null), noteKey(b.note ?? null)) || pos(a, b)
			: order === 'tasted'
				? Number(b.tasted) - Number(a.tasted) || Number(b.owned) - Number(a.owned) || pos(a, b)
				: order === 'todo'
					? Number(a.tasted) - Number(b.tasted) || pos(a, b)
					: order === 'region'
						? (a.region ?? '~').localeCompare(b.region ?? '~') || Number(b.tasted) - Number(a.tasted) || pos(a, b)
						: pos(a, b)
	);
}

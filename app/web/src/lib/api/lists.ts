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
}

export interface ListCard extends ListSummary {
	dots: { tasted: boolean; owned: boolean; region: string | null; color: string | null }[];
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

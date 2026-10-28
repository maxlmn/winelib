/** Forms: types, lookups and writes (see app/api/routers/forms.py). */
import { error } from '@sveltejs/kit';
import { appSettings } from '#lib/settings.svelte.ts';
import { forgetJournal } from './tastings.ts';
import { loadJson, request, RequestError } from './http.ts';

/** A picked row (id) or, with id null, a name to create on save. */
export interface Choice {
	id: number | null;
	name: string;
	/** something to make on save instead of an id: a lieu-dit of the map store ("lieu_dit:49060:les-poyeux") */
	ref?: string;
	hint?: string | null;
	/** a colour dot before the hint (a region's) */
	dot?: string | null;
}

export type Ref = number | { name: string };

export const toRef = (c: Choice | null): Ref | null => (c ? (c.id ?? { name: c.name }) : null);

export interface Region {
	id: number;
	name: string;
	country: string | null;
	color: string | null;
}

export interface Options {
	wine_types: string[];
	bottle_sizes: string[];
	currencies: string[];
	producer_types: string[];
	place_types: string[];
	locations: string[];
	ad_hoc: string;
	regions: Region[];
	/** the blend styles a wine can have (Bordeaux blend, Rhône blend...) */
	blend_styles: string[];
}

export interface WineSummary {
	id: number;
	producer_id: number;
	producer: string;
	cuvee: string;
	vintage: string | null;
	disgorgement_date: string | null;
	type: string | null;
	appellation: string | null;
	varietal: string | null;
	region: string | null;
	stock: number;
}

export interface BottleOption {
	id: number;
	wine_id: number;
	qty: number;
	bottle_size: string | null;
	location: string | null;
	label: string;
	wine: WineSummary;
}

export interface PlaceOption {
	id: number;
	name: string;
	city: string | null;
	country: string | null;
	type: string | null;
}

export interface ProducerOption {
	id: number;
	name: string;
	region_id: number | null;
	region: string | null;
}

type Named = { id: number; name: string } | null;

export interface ProducerForm {
	id: number;
	name: string;
	region: Named;
	subregion: string | null;
	village: string | null;
	winemaker: string | null;
	owner: string | null;
	type: string | null;
	importers: string | null;
	lists: string | null;
	profile_url: string | null;
	website: string | null;
	notes: string | null;
	description: string | null;
	aliases: string | null;
	wines: number;
}

export interface AppellationForm {
	id: number;
	name: string;
	region: Named;
	subregion: string | null;
	type: string | null;
	colors: string | null;
	varieties_text: string | null;
	location_link: string | null;
	details: string | null;
	aliases: string | null;
	wines: number;
}

export interface VineyardForm {
	id: number;
	name: string;
	region: Named;
	sub_region: string | null;
	village: string | null;
	wines: number;
}

export interface WineForm {
	id: number;
	producer: Named;
	cuvee: string | null;
	vintage: string | null;
	type: string | null;
	disgorgement_date: string | null;
	region: Named;
	appellation: Named;
	varietal: Named;
	/** its grapes in order, the first the main one */
	grapes: { varietal: Named; share: number | null }[];
	vineyard: Named;
	blend: string | null;
	lwin: string | null;
	drink_window_start: number | null;
	drink_window_end: number | null;
	summary: WineSummary;
	bottles: number;
}

export interface BottleDetails {
	bottle_size: string;
	price: number | null;
	currency: string;
	vendor: string | null;
	provenance: string | null;
	purchase_date: string | null;
}

export interface BottleForm extends BottleDetails {
	id: number;
	qty: number;
	location: string | null;
	last_price: number | null;
	last_price_date: string | null;
	last_price_source: string | null;
	option: BottleOption;
	wine: WineSummary;
	tastings: number;
}

export interface TastingForm {
	id: number;
	date: string | null;
	rating: number | null;
	glasses: number | null;
	sequence: number | null;
	tags: string | null;
	notes: string | null;
	/** the wine's style found in this tasting ("fresh", "mineral") */
	styles?: string[];
	place: PlaceOption | null;
	source: 'cellar' | 'other';
	bottle_id: number;
	bottle: BottleDetails;
	wine: WineSummary;
}

export interface PlaceForm {
	id: number;
	name: string;
	city: string | null;
	country: string | null;
	type: string | null;
	michelin_stars: number | null;
	notes: string | null;
	lat: number | null;
	lng: number | null;
	tastings: number;
	visits: number;
}

export interface VisitForm {
	id: number;
	date: string | null;
	notes: string | null;
	place: PlaceOption | null;
}

type Fetch = typeof fetch;

export const loadOptions = (fetch: Fetch) => loadJson<Options>(fetch, '/api/lookups/options');

/** An edit page's row (GET /api/forms/<kind>/<id>), or the 404 page. */
export async function loadForm<T>(fetch: Fetch, kind: string, id: string | null): Promise<T> {
	if (!id || !/^\d+$/.test(id)) error(404, 'Not found');
	const r = await fetch(`/api/forms/${kind}/${id}`);
	if (r.status === 404) error(404, (await r.json().catch(() => null))?.detail ?? 'Not found');
	if (!r.ok) error(r.status, `Could not load (${r.status})`);
	return r.json();
}

/** Like loadForm, for an optional ?query id: null when absent or gone. */
export async function loadOptional<T>(fetch: Fetch, kind: string, id: string | null): Promise<T | null> {
	if (!id || !/^\d+$/.test(id)) return null;
	const r = await fetch(`/api/forms/${kind}/${id}`);
	return r.ok ? r.json() : null;
}

export async function lookup<T>(kind: string, params: Record<string, string | number | null | undefined>): Promise<T[]> {
	const p = new URLSearchParams();
	for (const [k, v] of Object.entries(params)) if (v !== null && v !== undefined && v !== '') p.set(k, String(v));
	const r = await fetch(`/api/lookups/${kind}?${p}`);
	return r.ok ? r.json() : [];
}

/** A rejected save: one message for the banner, and per-field messages where the API says which field. */
export { RequestError as FormError } from './http.ts';

/** A form's request: its JSON, or a FormError with the server's message (per field when it named them) */
export async function send<T = { id: number }>(method: 'POST' | 'PUT' | 'DELETE', url: string, body?: unknown): Promise<T> {
	const out = await request<T>(url, { method, body });
	forgetJournal(); // the tasting journal, kept between pages, is read again
	return out;
}

/** Create (POST /api/<kind>) or update (PUT /api/<kind>/<id>). */
export const save = <T = { id: number }>(kind: string, id: number | null, body: unknown) =>
	send<T>(id ? 'PUT' : 'POST', id ? `/api/${kind}/${id}` : `/api/${kind}`, body);

export const remove = <T = { deleted: number }>(kind: string, id: number) => send<T>('DELETE', `/api/${kind}/${id}`);

export const today = () => {
	const d = new Date();
	return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};

/** "2020", or "NV - Oct 2024" for a disgorged NV. */
export const vintageLabel = (w: Pick<WineSummary, 'vintage' | 'disgorgement_date'>) =>
	w.vintage === 'NV' && w.disgorgement_date ? `NV - ${w.disgorgement_date}` : (w.vintage ?? '');

const fold = (s: string) => s.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase();

/** Filter a short list already in memory (regions) the way the API filters lookups. */
export const filterNamed = <T extends { name: string }>(rows: T[], q: string) =>
	rows.filter((r) => fold(r.name).includes(fold(q.trim())));

export const blank =(s: string | null | undefined) => s ?? '';

export const num = (v: number | string | null | undefined) => (v === '' || v === null || v === undefined || Number.isNaN(+v) ? null : +v);

/** The wine fields as edited (a producer / region / appellation / varietal may be new). */
export interface WineDraft {
	producer: Choice | null;
	producerRegion: Choice | null;
	cuvee: string;
	vintage: string;
	type: string;
	disgorgement_date: string;
	region: Choice | null;
	appellation: Choice | null;
	/** its grapes in order (the first the main one), each with its share in percent when known */
	grapes: GrapeDraft[];
	vineyard: Choice | null;
	blend: string;
	lwin: string;
	drink_window_start: number | null;
	drink_window_end: number | null;
}

export interface GrapeDraft {
	varietal: Choice | null;
	share: number | null;
}

const choice = (n: Named): Choice | null => (n ? { id: n.id, name: n.name } : null);
export const emptyGrape = (): GrapeDraft => ({ varietal: null, share: null });

export function emptyWine(producer: Choice | null = null, region: Choice | null = null): WineDraft {
	return {
		producer, producerRegion: null, cuvee: '', vintage: '', type: 'Red', disgorgement_date: '', region,
		appellation: null, grapes: [emptyGrape()], vineyard: null, blend: '', lwin: '',
		drink_window_start: null, drink_window_end: null
	};
}

export function wineDraft(w: WineForm): WineDraft {
	return {
		producer: choice(w.producer), producerRegion: null, cuvee: blank(w.cuvee), vintage: blank(w.vintage),
		type: w.type ?? 'Red', disgorgement_date: blank(w.disgorgement_date), region: choice(w.region),
		appellation: choice(w.appellation), vineyard: choice(w.vineyard),
		grapes: w.grapes?.length
			? w.grapes.map((g) => ({ varietal: choice(g.varietal), share: g.share }))
			: [{ varietal: choice(w.varietal), share: null }],
		blend: blank(w.blend), lwin: blank(w.lwin), drink_window_start: w.drink_window_start, drink_window_end: w.drink_window_end
	};
}

/** "New Vintage": same wine, blank vintage and disgorgement. */
export const newVintageDraft = (w: WineForm): WineDraft => ({
	...wineDraft(w), vintage: '', disgorgement_date: ''
});

export function toWineIn(d: WineDraft) {
	const producer = d.producer?.id ?? (d.producer ? { name: d.producer.name, region: toRef(d.producerRegion) } : null);
	return {
		producer, cuvee: d.cuvee, vintage: d.vintage, type: d.type,
		disgorgement_date: d.type?.startsWith('Bubbles') ? d.disgorgement_date : null,
		region: toRef(d.region), appellation: toRef(d.appellation),
		grapes: d.grapes.filter((g) => g.varietal).map((g) => ({ varietal: toRef(g.varietal), share: num(g.share) })),
		vineyard: d.vineyard?.ref ?? d.vineyard?.id ?? null, blend: d.blend || null, lwin: d.lwin, drink_window_start: d.drink_window_start, drink_window_end: d.drink_window_end
	};
}

/** Client-side checks before a wine is sent; keys match the API's field names. */
export const wineErrors = (d: WineDraft, prefix = ''): Record<string, string> =>
	d.producer ? {} : { [`${prefix}producer`]: 'Pick a producer, or type a new name' };

/** The errors of a nested part of the payload ("wine.producer" -> "producer"). */
export const scoped = (errors: Record<string, string>, part: string) =>
	Object.fromEntries(Object.entries(errors).filter(([k]) => k.startsWith(`${part}.`)).map(([k, v]) => [k.slice(part.length + 1), v]));

/** Throws the client-side problems found before sending, like a rejected save would. */
export function check(problems: Record<string, string>) {
	if (Object.keys(problems).length) throw new RequestError(Object.values(problems).join(' · '), problems);
}

/** The bottle-details fields as edited. */
export interface BottleDraft {
	bottle_size: string;
	price: number | null;
	currency: string;
	vendor: string;
	provenance: string;
	purchase_date: string;
}

export const bottleDraft = (b?: BottleDetails | null, provenance = ''): BottleDraft => ({
	bottle_size: b?.bottle_size ?? '75cl', price: b?.price ?? null, currency: b?.currency ?? appSettings.currency,
	vendor: blank(b?.vendor), provenance: b ? blank(b.provenance) : provenance,
	purchase_date: b ? blank(b.purchase_date) : today()
});

export const toBottleDetails = (d: BottleDraft) => ({ ...d, purchase_date: d.purchase_date || null });

export interface PlaceChoice extends Choice {
	city?: string | null;
	country?: string | null;
	type?: string | null;
}

export const placeChoice = (p: PlaceOption | null): PlaceChoice | null =>
	p ? { id: p.id, name: p.name, hint: placeHint(p), city: p.city, country: p.country, type: p.type } : null;

export const placeHint = (p: Pick<PlaceOption, 'city' | 'country'>) => [p.city, p.country].filter(Boolean).join(', ');

export const toPlaceRef = (p: PlaceChoice | null) =>
	p ? (p.id ?? { name: p.name, city: p.city || null, country: p.country || null, type: p.type || null }) : null;

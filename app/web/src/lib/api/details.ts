import type { Family } from './grapes.ts';
import { regionColorsByName } from '#lib/regions.svelte.ts';
import { error } from '@sveltejs/kit';
import type { Bottle, MapCollection, RegionCollection, RegionColors } from '#lib/types.ts';

type Fetch = typeof fetch;

export interface Ref {
	id: number;
	name: string;
}

export interface RegionInfo {
	region: string | null;
	region_color: string | null;
}

export interface CellarTotals {
	bottles: number;
	/** market value, in the main currency */
	value: number;
}

export interface TastingPlace {
	id: number;
	name: string;
	city: string | null;
	country: string | null;
	type?: string | null;
	michelin_stars: number | null;
}

export interface Tasting extends RegionInfo {
	id: number;
	date: string | null;
	rating: number | null;
	notes: string | null;
	glasses: number | null;
	/** the occasion's photo (place and day), if any */
	photo: string | null;
	place: TastingPlace | null;
	/** free-text location when there is no place */
	location: string | null;
	bottle_id: number;
	format: string | null;
	price_base: number;
	wine_id: number;
	producer_id: number;
	producer: string;
	cuvee: string;
	appellation: string | null;
	vintage: string;
	color: string | null;
	/** the preferred critic\'s score (Settings): sorting */
	score?: string | null;
	/** every critic\'s score, "RP 95 · VI 94" */
	scores?: string | null;
}

export interface Visit {
	id: number;
	date: string | null;
	notes: string | null;
	photo: string | null;
}

export interface VintageRef {
	id: number;
	vintage: string;
	bottles: number;
	tastings: number;
	/** the preferred critic\'s score (Settings): sorting */
	score?: string | null;
	/** every critic\'s score, "RP 95 · VI 94" */
	scores?: string | null;
	/** the lists naming this vintage */
	lists?: string[];
}

/** A cuvée (same cuvée, appellation and grape) with all its vintages */
export interface CatalogEntry {
	cuvee: string;
	producer_id: number;
	producer: string;
	appellation: Ref | null;
	varietal: string | null;
	color: string | null;
	vintages: VintageRef[];
	/** the lists naming the cuvée, any vintage */
	lists?: string[];
}

export interface ProducerDetail extends RegionInfo {
	id: number;
	name: string;
	subregion: string | null;
	village: string | null;
	winemaker: string | null;
	owner: string | null;
	type: string | null;
	importers: string | null;
	description: string | null;
	notes: string | null;
	website: string | null;
	profile_url: string | null;
	/** other names it goes by, comma separated */
	aliases: string | null;
	stats: CellarTotals & { tastings: number; wines: number };
	wines: CatalogEntry[];
	/** where the wines come from, most tasted first: wines, bottles in the cellar and tastings each */
	appellations: PlaceCount[];
	vineyards: (PlaceCount & { village: string | null; subregion: string | null })[];
	cellar: Bottle[];
	tastings: Tasting[];
}

export interface PlaceCount {
	id: number;
	name: string;
	wines: number;
	bottles: number;
	tastings: number;
}

export interface CriticScore {
	critic: string;
	score: string | null;
	note: string | null;
	url: string | null;
	date: string | null;
}

/** A button a plug-in adds to the wine page (app/api/plugins.py): POST to the endpoint, show the answer's message */
export interface WineAction {
	id: string;
	label: string;
	endpoint: string;
	/** drawn on that critic's line of the Critics card (else next to Add a score) */
	critic: string | null;
	busy: string | null;
	confirm: string | null;
}

export interface WineDetail extends RegionInfo {
	id: number;
	producer: Ref;
	cuvee: string;
	vintage: string;
	disgorgement_date: string | null;
	color: string | null;
	appellation: Ref | null;
	vineyard: (Ref & { label: string }) | null;
	varietal: string | null;
	blend: string | null;
	/** its grapes in order, the main one first, with their share when known */
	grapes: { id: number; name: string; share: number | null }[];
	lwin: string | null;
	/** the other critics' scores */
	scores: CriticScore[];
	actions: WineAction[];
	drink_window: [number | null, number | null];
	maturity: import('#lib/maturity.ts').Maturity;
	/** every vintage of this cuvée, this one included */
	vintages: VintageRef[];
	/** the lists naming the cuvée, any vintage */
	cuvee_lists?: string[];
	/** bottles and tastings of all those vintages */
	cellar: Bottle[];
	tastings: Tasting[];
}

export interface BottleDetail {
	id: number;
	wine_id: number;
	qty: number;
	bottle_size: string | null;
	location: string | null;
	location_group: string;
	price: number | null;
	currency: string | null;
	price_base: number | null;
	last_price: number | null;
	last_price_date: string | null;
	last_price_source: string | null;
	change_pct: number | null;
	vendor: string | null;
	provenance: string | null;
	purchase_date: string | null;
}

export interface PlaceDetail {
	id: number;
	name: string;
	city: string | null;
	country: string | null;
	type: string | null;
	michelin_stars: number | null;
	notes: string | null;
	lat: number | null;
	lng: number | null;
	stats: { visits: number; tastings: number; value: number };
	visits: Visit[];
	tastings: Tasting[];
}

export interface AppellationDetail extends RegionInfo {
	id: number;
	name: string;
	subregion: string | null;
	type: string | null;
	category: string | null;
	pdo_id: string | null;
	registration_date: string | null;
	max_yield_hl: number | null;
	max_yield_kg: number | null;
	varieties: string | null;
	details: string | null;
	/** other names it goes by, comma separated */
	aliases: string | null;
	bottles: number;
	colors: string | null;
	location_link: string | null;
	/** the shape store has its outline at full detail (DetailMap's toggle) */
	full_outline: boolean;
	stats: CellarTotals & { tastings: number };
	producers: (Ref & { wines: number })[];
	/** the vineyards of its wines */
	vineyards: (Ref & { village: string | null; wines: number })[];
	cellar: Bottle[];
	tastings: Tasting[];
}

export interface VineyardDetail extends RegionInfo {
	id: number;
	name: string;
	subregion: string | null;
	village: string | null;
	bottles: number;
	vineyard_id: number | null;
	/** the shape store has its outline at full detail (DetailMap's toggle) */
	full_outline: boolean;
	appellations: Ref[];
	stats: CellarTotals & { tastings: number };
	wines: CatalogEntry[];
	cellar: Bottle[];
	tastings: Tasting[];
}

export interface RegionDetail {
	id: number;
	name: string;
	country: string | null;
	color: string | null;
	stats: CellarTotals & { tastings: number; producers: number; appellations: number; vineyards: number };
	appellations: (Ref & { subregion: string | null; type: string | null; bottles: number; tastings: number })[];
	producers: (Ref & { subregion: string | null; village: string | null; wines: number; bottles: number; tastings: number })[];
	cellar: Bottle[];
	tastings: Tasting[];
}

export interface GrapeDetail {
	id: number;
	name: string;
	aliases: string | null;
	/** VIVC's facts: its berries' colour, its country of origin, its passport */
	color: string | null;
	origin: string | null;
	vivc: { number: number; url: string } | null;
	family: Family;
	/** its tasting profile (climate, acidity, tannin, aromas...), classic regions and notes */
	profile: {
		facts: { label: string; value: string }[];
		notes: string | null;
		regions: string[];
	} | null;
	stats: CellarTotals & { tastings: number; producers: number; regions: number; wines: number };
	regions: { name: string; color: string | null; wines: number; bottles: number; tastings: number }[];
	producers: (Ref & { region: string | null; wines: number; bottles: number; tastings: number })[];
	cellar: Bottle[];
	tastings: Tasting[];
}

export interface VintageRow {
	vintage: string;
	wines: number;
	bottles: number;
	tastings: number;
	/** the bottles and tastings by region, biggest first */
	regions: { region: string | null; bottles: number; tastings: number }[];
}

export interface VintageDetail {
	vintage: string;
	prev: string | null;
	next: string | null;
	stats: CellarTotals & { tastings: number; wines: number; producers: number; regions: number; critic: string; score_mine: number | null; score_count: number };
	regions: { name: string; color: string | null; wines: number; bottles: number; tastings: number }[];
	/** the preferred critic's best scores of the vintage, highest first */
	best: { id: number; producer: string; cuvee: string; appellation: string | null; color: string | null; score: string; scores?: string | null; bottles: number; tastings: number }[];
	wines: CatalogEntry[];
	cellar: Bottle[];
	tastings: Tasting[];
}

export interface Shapes {
	appellations: MapCollection;
	vineyards: MapCollection;
	/** region pages: the region's outline, as context */
	region?: Omit<RegionCollection, 'extent'>;
	/** whether any outlines are installed (the shape store): without, the map says where to get them */
	outlines?: boolean;
}

export type ShapesOf = 'regions' | 'producers' | 'wines' | 'appellations' | 'vineyards';

export const shapesUrl = (kind: ShapesOf, id: number | string) => `/api/${kind}/${encodeURIComponent(String(id))}/shapes`;

async function getJson<T>(fetch: Fetch, url: string, what: string): Promise<T> {
	const r = await fetch(url);
	// a non-numeric id is a 422
	if (r.status === 404 || r.status === 422) error(404, `${what} not found`);
	if (!r.ok) error(r.status, `Couldn’t load the ${what.toLowerCase()}`);
	return r.json();
}

/** One detail record plus the region palette the cellar cards and history need (loaded once by the layout). */
async function withColors<T>(fetch: Fetch, url: string, what: string) {
	return { detail: await getJson<T>(fetch, url, what), regionColors: regionColorsByName as RegionColors };
}

export const loadProducer = (fetch: Fetch, id: string) => withColors<ProducerDetail>(fetch, `/api/producers/${id}`, 'Producer');
export const loadWine = (fetch: Fetch, id: string | number) => withColors<WineDetail>(fetch, `/api/wines/${id}`, 'Wine');
export const loadPlace = (fetch: Fetch, id: string) => withColors<PlaceDetail>(fetch, `/api/places/${id}`, 'Place');
export const loadAppellation = (fetch: Fetch, id: string) =>
	withColors<AppellationDetail>(fetch, `/api/appellations/${id}`, 'Appellation');
export const loadVineyard = (fetch: Fetch, id: string) => withColors<VineyardDetail>(fetch, `/api/vineyards/${id}`, 'Vineyard');
/** By id or name: pages that only know a region's name link to it by name */
export const loadRegion = (fetch: Fetch, key: string) =>
	withColors<RegionDetail>(fetch, `/api/regions/${encodeURIComponent(key)}`, 'Region');
export const loadGrape = (fetch: Fetch, key: string) =>
	withColors<GrapeDetail>(fetch, `/api/grapes/${encodeURIComponent(key)}`, 'Grape');
export const loadVintage = (fetch: Fetch, year: string) =>
	withColors<VintageDetail>(fetch, `/api/vintages/${encodeURIComponent(year)}`, 'Vintage');
export const loadVintages = (fetch: Fetch) => getJson<VintageRow[]>(fetch, '/api/vintages', 'Vintages');
export const loadBottle = (fetch: Fetch, id: string) => getJson<BottleDetail>(fetch, `/api/bottles/${id}`, 'Bottle');

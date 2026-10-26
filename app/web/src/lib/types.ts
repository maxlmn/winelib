export interface Bottle {
	bottle_id: number;
	wine_id: number;
	producer_id: number;
	appellation_id: number | null;
	location: string;
	location_group: string;
	/** counted in the local totals (Settings: locations without its keywords) */
	local: boolean;
	qty: number;
	format: string | null;
	color: string | null;
	region: string;
	producer: string;
	cuvee: string;
	appellation: string | null;
	varietal: string | null;
	/** every grape of the wine, main first (the Grape filter matches any) */
	grapes: string[];
	vintage: string;
	price: number | null;
	currency: string | null;
	last_price: number | null;
	price_base: number;
	market_base: number;
	/** the preferred critic\'s score (Settings): sorting */
	score?: string | null;
	/** every critic\'s score, "RP 95 · VI 94" */
	scores?: string | null;
	lwin: string | null;
	purchase_date: string | null;
	/** drinking window (set on the wine) and where the wine stands in it */
	drink_from: number | null;
	drink_to: number | null;
	maturity: import('#lib/maturity.ts').Maturity;
}

export interface Location {
	name: string;
	group: string;
	capacity: number | null;
}

export interface CellarData {
	bottles: Bottle[];
	locations: Location[];
}

export type RegionColors = Record<string, string>;

export interface MapProps {
	id: number;
	kind: 'appellation' | 'vineyard';
	name: string;
	bottles: number;
	value: number;
	tastings: number;
	region?: string | null;
	color?: string;
	subregion?: string | null;
	village?: string | null;
	type?: string | null;
	/** 2 grand cru, 1 premier cru, 0 otherwise: drawn that many notches darker */
	cru?: number;
	/** vineyards: village shade, set by the map */
	fill?: string;
	edge?: string;
}

export interface MapCollection {
	type: 'FeatureCollection';
	features: import('geojson').Feature<import('geojson').Geometry, MapProps>[];
	missing: string[];
}

export interface MapRegion {
	id: number;
	name: string;
	country: string | null;
	color: string;
	appellations: number;
	vineyards: number;
	/** yours: bottles in the cellar (and their value, in the main currency) and tasting notes, by the wine's region */
	bottles: number;
	value: number;
	tastings: number;
}

/** A region on the map's overview (GET /api/map/overview): one coarse outline each */
export type RegionProps = MapRegion & { kind: 'region'; bbox: [number, number, number, number] | null };
export interface RegionCollection {
	type: 'FeatureCollection';
	features: import('geojson').Feature<import('geojson').Geometry | null, RegionProps>[];
	extent: [number, number, number, number] | null;
	/** the overview: whether any appellation / vineyard outlines are installed (the shape store) */
	outlines?: boolean;
}

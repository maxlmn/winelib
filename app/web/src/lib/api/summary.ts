type Fetch = typeof fetch;

export interface Count {
	name: string;
	count: number;
}

export interface Ranked extends Count {
	id: number;
	region: string;
	color: string;
}

/** Tastings or bottles, broken down. `total` is what the percentages are of. */
export interface Breakdown {
	total: number;
	wines: number;
	colors: Count[];
	regions: (Count & { color: string })[];
	producers: Ranked[];
	appellations: Ranked[];
	/** most common first; a last entry with name null sums the other `grapes` */
	grapes: { name: string | null; count: number; type: string | null; grapes?: number }[];
	/** each split by region, biggest first */
	vintages: (Count & { regions: (Count & { color: string })[] })[];
}

/** A wine in a highlight card */
export interface HighlightWine {
	wine_id: number;
	producer: string;
	cuvee: string;
	vintage: string;
	region: string | null;
	color: string | null;
	format: string | null;
}

export interface TastingSummary extends Breakdown {
	rated: number;
	avg_rating: number | null;
	michelin: {
		/** stars of the distinct restaurants visited */
		unique_stars: number;
		/** stars summed over every visit day */
		total_stars: number;
		restaurants: { stars: number; count: number }[];
	};
	highlights: {
		/** each wine once, at its best score */
		best: (HighlightWine & { id: number; rating: number; date: string | null })[];
		/** days at each place, with or without wine */
		places: { id: number; name: string; type: string | null; city: string | null; visits: number }[];
		/** the occasion with the most wines, in the order poured */
		evening: { date: string; place_id: number | null; place: string | null; wines: (HighlightWine & { id: number })[] } | null;
	};
}

export interface CellarSummary extends Breakdown {
	/** purchase price, in the main currency */
	value: number;
	/** last known market price, in the main currency */
	market: number;
	highlights: {
		largest: (HighlightWine & { qty: number })[];
		oldest: (HighlightWine & { qty: number })[];
		/** bottles by storage group */
		storage: Count[];
	};
}

export const getTastingSummary = (fetch: Fetch) =>
	fetch('/api/summary/tastings').then((r) => r.json() as Promise<TastingSummary>);

export const getCellarSummary = (fetch: Fetch) =>
	fetch('/api/summary/cellar').then((r) => r.json() as Promise<CellarSummary>);

type Fetch = typeof fetch;

export interface ProducerRow {
	id: number;
	name: string;
	region: string | null;
	color: string | null;
	subregion: string | null;
	village: string | null;
	winemaker: string | null;
	/** the lists it's on (itself or one of its wines), by name: the Lists filter */
	lists: string[];
	/** the same, with their ids: a link to each */
	list_refs: { id: number; name: string }[];
	notes: string | null;
	tastings: number;
	bottles: number;
}

export interface PlaceRow {
	id: number;
	name: string;
	city: string | null;
	country: string | null;
	type: string | null;
	stars: number;
	notes: string | null;
	lat: number | null;
	lng: number | null;
	/** distinct days there, with or without wine */
	visits: number;
	last_visit: string | null;
	tastings: number;
}

export const getProducers = (fetch: Fetch) => fetch('/api/producers').then((r) => r.json() as Promise<ProducerRow[]>);

export const getPlaces = (fetch: Fetch) => fetch('/api/places').then((r) => r.json() as Promise<PlaceRow[]>);

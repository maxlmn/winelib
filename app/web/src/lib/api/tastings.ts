import { invalidate } from '$app/navigation';

export interface Tasting {
	id: number;
	date: string;
	seq: number | null;
	glasses: number | null;
	rating: number | null;
	notes: string;
	place_id: number | null;
	/** place name, or the free-text location when there is no place */
	location: string;
	bottle_id: number;
	format: string | null;
	wine_id: number;
	color: string | null;
	producer_id: number;
	producer: string;
	cuvee: string;
	appellation_id: number | null;
	appellation: string | null;
	varietal: string | null;
	/** every grape of the wine, main first (the Grape filter matches any) */
	grapes: string[];
	region: string;
	vintage: string;
	/** the preferred critic\'s score (Settings): sorting */
	score?: string | null;
	/** every critic\'s score, "RP 95 · VI 94" */
	scores?: string | null;
}

export interface Visit {
	id: number;
	date: string;
	place_id: number;
	notes: string;
}

export interface Place {
	id: number;
	name: string;
	city: string | null;
	country: string | null;
	type: string | null;
	stars: number;
	lat: number | null;
	lng: number | null;
}

export interface Journal {
	tastings: Tasting[];
	visits: Visit[];
	places: Record<string, Place>;
	/** lowercased "<place>_<YYYY-MM-DD>" -> photo URL */
	photos: Record<string, string>;
}

interface WineBrief {
	wine_id: number;
	producer: string;
	cuvee: string;
	vintage: string;
	color: string | null;
	region?: string | null;
	appellation?: string | null;
}

export interface TastingDetail {
	id: number;
	date: string;
	seq: number | null;
	glasses: number | null;
	rating: number | null;
	notes: string;
	tags: string | null;
	/** the wine's style found that day ("fresh", "mineral") */
	styles?: string[];
	location: string | null;
	place: Place | null;
	photo: string | null;
	bottle: {
		id: number;
		format: string | null;
		location: string | null;
		qty: number | null;
		vendor: string | null;
		provenance: string | null;
		price: number | null;
		currency: string | null;
		price_base: number | null;
		purchase_date: string | null;
	};
	wine: {
		id: number;
		producer_id: number;
		producer: string;
		cuvee: string;
		vintage: string;
		disgorged: string | null;
		color: string | null;
		region: string | null;
		region_color: string | null;
		appellation: { id: number; name: string } | null;
		vineyard: { id: number; label: string } | null;
		varietal: string | null;
		blend: string | null;
		/** its grapes in order, the main one first, with their share when known */
		grapes: { id: number; name: string; share: number | null }[];
		lwin: string | null;
		/** every critic's score, the preferred one first */
		scores: { critic: string; score: string | null; note: string | null; url: string | null }[];
		drink_from: number | null;
		drink_to: number | null;
	};
	occasion: (WineBrief & { id: number; seq: number | null; glasses: number | null; rating: number | null; notes?: string; score?: string | null; scores?: string | null })[];
	history: (WineBrief & { id: number; date: string; place: string | null; place_id: number | null; rating: number | null; score?: string | null; scores?: string | null; notes: string })[];
}

type Fetch = typeof fetch;

/* The journal is every tasting (thousands): kept in the browser between visits. A page shows the copy at hand at
 * once and refreshes it in the background (a nightly job, a change made elsewhere), redrawing only if it changed.
 * The app's own saves (forms, photos) call forgetJournal, so the next page waits for the fresh one instead. */
export const JOURNAL = 'app:journal';
let kept: { journal: Journal; text: string; at: number } | null = null;
let stale = false;
let pending: Promise<boolean> | null = null;

/** Downloads the journal; true if it differs from the copy kept */
function download(fetch: Fetch): Promise<boolean> {
	pending ??= fetch('/api/tastings')
		.then(async (r) => {
			if (!r.ok) throw new Error(`Tastings: ${r.status}`);
			const text = await r.text();
			const changed = text !== kept?.text;
			kept = { journal: changed ? (JSON.parse(text) as Journal) : kept!.journal, text, at: Date.now() };
			stale = false;
			return changed;
		})
		.finally(() => (pending = null));
	return pending;
}

export async function fetchJournal(fetch: Fetch): Promise<Journal> {
	if (!kept || stale) {
		await download(fetch);
		return kept!.journal;
	}
	// Shown as kept; checked again unless it was just downloaded (a redraw after a refresh lands here too)
	if (Date.now() - kept.at > 2000)
		download(globalThis.fetch)
			.then((changed) => {
				if (changed) invalidate(JOURNAL);
			})
			.catch(() => {});
	return kept.journal;
}

/** Fetches the journal ahead of a visit to the tasting notes (the app calls it once idle) */
export const warmJournal = () => {
	if (!kept) download(globalThis.fetch).catch(() => {});
};

/** After a save: the next tasting page waits for the fresh journal */
export const forgetJournal = () => {
	stale = true;
};

export async function fetchTasting(fetch: Fetch, id: string | number): Promise<TastingDetail | null> {
	const r = await fetch(`/api/tastings/${id}`);
	return r.ok ? r.json() : null;
}

/** Home page data (GET /api/dashboard). */

export interface WineRef {
	wine_id: number;
	producer_id: number;
	producer: string;
	cuvee: string;
	/** shown instead of the cuvée when it has no name */
	appellation: string | null;
	varietal: string | null;
	/** the preferred critic's score (Settings): sorting */
	score?: string | null;
	/** every critic's score, "RP 95 · VI 94" */
	scores?: string | null;
	vintage: string;
	color: string | null;
	region: string | null;
}

export interface Occasion {
	date: string;
	place: string;
	place_id: number | null;
	stars: number | null;
	/** wines tasted that day there (the first few are listed) */
	count: number;
	wines: (WineRef & { id: number; format: string | null })[];
}

export interface Purchase extends WineRef {
	bottle_id: number;
	date: string | null;
	qty: number;
	location: string | null;
	format: string | null;
	price: number | null;
	currency: string | null;
	price_base: number | null;
}

export interface Nudge {
	region: string;
	color: string | null;
	bottles: number;
	last_tasted: string | null;
}

export interface DrinkSoonLine {
	bottle_id: number;
	wine_id: number;
	producer: string;
	cuvee: string;
	appellation: string | null;
	varietal: string | null;
	vintage: string;
	color: string | null;
	region: string;
	qty: number;
	location: string;
	format: string | null;
	/** the preferred critic\'s score (Settings): sorting */
	score?: string | null;
	/** every critic's score, "RP 95 · VI 94" */
	scores?: string | null;
	drink_from: number | null;
	drink_to: number | null;
	maturity: 'ready' | 'past';
	years_left: number | null;
}

export interface Dashboard {
	today: string;
	cellar: { bottles: number; cost: number; market: number };
	year: { tastings: number; purchases: number };
	occasions: Occasion[];
	purchases: Purchase[];
	nudges: Nudge[];
	/** past their drinking window first, then those closing soonest; and bottles by maturity */
	drink_soon: { lines: DrinkSoonLine[]; bottles: { ready: number; young: number; past: number; unknown: number } };
}

export async function loadDashboard(fetch: typeof globalThis.fetch): Promise<Dashboard> {
	const res = await fetch('/api/dashboard');
	if (!res.ok) throw new Error(`Couldn’t load the home page (${res.status})`);
	return res.json();
}

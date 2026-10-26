/** About the data (GET /api/about/data): the sources and how it was built (Markdown, app/api/data/docs/), what this
 * database holds, and the installed map outlines' credits. */
import type { MapCredit } from '#lib/settings.svelte.ts';

type Fetch = typeof fetch;

export interface AboutData {
	sources: string;
	built: string;
	counts: {
		regions: number;
		countries: number;
		appellations: number;
		appellations_outlined: number;
		vineyards: number;
		vineyards_outlined: number;
		grapes: number;
		grapes_vivc: number;
		grapes_parents: number;
		grapes_profile: number;
	};
	by_country: { name: string; count: number }[];
	by_type: { name: string; count: number }[];
	map_credits: MapCredit[];
}

export const getAboutData = (fetch: Fetch) => fetch('/api/about/data').then((r) => r.json() as Promise<AboutData>);

import { getCellarSummary, getTastingSummary } from '#lib/api/summary.ts';
import type { CellarData } from '#lib/types.ts';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
	// the cellar's bottles too: their value and number by storage place (the donuts)
	const [tastings, cellar, bottles] = await Promise.all([
		getTastingSummary(fetch),
		getCellarSummary(fetch),
		fetch('/api/cellar').then((r) => (r.ok ? (r.json() as Promise<CellarData>).then((d) => d.bottles) : []))
	]);
	return { tastings, cellar, bottles };
};

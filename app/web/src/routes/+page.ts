import { loadDashboard } from '#lib/api/dashboard.ts';
import { JOURNAL, fetchJournal } from '#lib/api/tastings.ts';
import { regionColorsByName } from '#lib/regions.svelte.ts';
import type { CellarData, RegionColors } from '#lib/types.ts';

export const load = async ({ fetch, depends }) => {
	depends(JOURNAL);
	const [dashboard, journal, cellar] = await Promise.all([
		loadDashboard(fetch),
		fetchJournal(fetch),
		fetch('/api/cellar').then((r) => r.json() as Promise<CellarData>)
	]);
	return { dashboard, journal, cellar, regionColors: regionColorsByName as RegionColors };
};

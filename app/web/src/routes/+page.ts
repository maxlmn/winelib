import { loadDashboard } from '#lib/api/dashboard.ts';
import { JOURNAL, fetchJournal } from '#lib/api/tastings.ts';
import { regionColorsByName } from '#lib/regions.svelte.ts';
import type { CellarData, RegionColors } from '#lib/types.ts';
import type { AttentionItem } from '#lib/components/home/Attention.svelte';

export const load = async ({ fetch, depends }) => {
	depends(JOURNAL);
	const [dashboard, journal, cellar, attention] = await Promise.all([
		loadDashboard(fetch),
		fetchJournal(fetch),
		fetch('/api/cellar').then((r) => r.json() as Promise<CellarData>),
		// what needs attention: the page shows without it when it fails
		fetch('/api/attention')
			.then((r) => (r.ok ? (r.json() as Promise<{ items: AttentionItem[] }>) : { items: [] }))
			.catch(() => ({ items: [] as AttentionItem[] }))
	]);
	return { dashboard, journal, cellar, attention: attention.items, regionColors: regionColorsByName as RegionColors };
};

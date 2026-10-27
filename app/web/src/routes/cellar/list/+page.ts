import { regionColorsByName } from '#lib/regions.svelte.ts';
import type { ListCard, ListDetail } from '#lib/api/lists.ts';
import type { CellarData, RegionColors } from '#lib/types.ts';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, url }) => {
	// From one of your lists (?from=<id>): its entries, to print your bottles of them or the whole list
	const from = url.searchParams.get('from');
	const [cellar, lists, list] = await Promise.all([
		fetch('/api/cellar').then((r) => r.json() as Promise<CellarData>),
		fetch('/api/lists').then((r) => (r.ok ? (r.json() as Promise<ListCard[]>) : [])),
		from ? fetch(`/api/lists/${from}`).then((r) => (r.ok ? (r.json() as Promise<ListDetail>) : null)) : null
	]);
	return { cellar, lists, list, regionColors: regionColorsByName as RegionColors };
};

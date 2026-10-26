import { regionColorsByName } from '#lib/regions.svelte.ts';
import type { CellarData, RegionColors } from '#lib/types.ts';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
	const cellar = await fetch('/api/cellar').then((r) => r.json() as Promise<CellarData>);
	return { cellar, regionColors: regionColorsByName as RegionColors };
};

import { JOURNAL, fetchJournal } from '#lib/api/tastings.ts';
import { regionColorsByName } from '#lib/regions.svelte.ts';
import type { RegionColors } from '#lib/types.ts';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, depends }) => {
	depends(JOURNAL);
	return { journal: await fetchJournal(fetch), regionColors: regionColorsByName as RegionColors };
};

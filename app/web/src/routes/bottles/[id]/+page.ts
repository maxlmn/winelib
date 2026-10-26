import { loadBottle, loadWine } from '#lib/api/details.ts';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, params }) => {
	const bottle = await loadBottle(fetch, params.id);
	return { bottle, ...(await loadWine(fetch, bottle.wine_id)) };
};

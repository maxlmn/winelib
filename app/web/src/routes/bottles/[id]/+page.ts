import { redirect } from '@sveltejs/kit';
import { loadBottle } from '#lib/api/details.ts';
import { links } from '#lib/links.ts';
import type { PageLoad } from './$types';

// A bottle is a card on its wine's page: the old address goes there
export const load: PageLoad = async ({ fetch, params }) => {
	const bottle = await loadBottle(fetch, params.id);
	redirect(307, links.wineBottle(bottle.wine_id, bottle.id));
};

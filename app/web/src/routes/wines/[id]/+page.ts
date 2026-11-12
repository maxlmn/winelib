import { loadBottle, loadWine } from '#lib/api/details.ts';
import type { PageLoad } from './$types';

// ?bottle=N: that bottle of the wine, a card on its page (a cellar line clicked)
export const load: PageLoad = async ({ fetch, params, url }) => {
	const id = url.searchParams.get('bottle');
	const [wine, bottle] = await Promise.all([loadWine(fetch, params.id), id ? loadBottle(fetch, id).catch(() => null) : null]);
	return { ...wine, bottle: bottle && String(bottle.wine_id) === params.id ? bottle : null };
};

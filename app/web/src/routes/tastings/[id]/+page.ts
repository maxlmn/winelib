import { error } from '@sveltejs/kit';
import { fetchTasting } from '#lib/api/tastings.ts';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, params }) => {
	const tasting = await fetchTasting(fetch, params.id);
	if (!tasting) error(404, 'Tasting not found');
	return { tasting };
};

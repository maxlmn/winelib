import { error } from '@sveltejs/kit';
import { getGuide } from '#lib/api/help.ts';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, params }) => {
	const guide = await getGuide(fetch, params.slug);
	if (!guide) error(404, 'No such guide');
	return { guide };
};

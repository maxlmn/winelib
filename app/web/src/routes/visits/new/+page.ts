import { loadOptional, loadOptions } from '#lib/api/forms.ts';
import type { PlaceOption } from '#lib/api/forms.ts';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, url }) => {
	const [options, place] = await Promise.all([
		loadOptions(fetch),
		loadOptional<PlaceOption>(fetch, 'places', url.searchParams.get('place_id'))
	]);
	return { options, place };
};

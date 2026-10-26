import { loadForm, loadOptions } from '#lib/api/forms.ts';
import type { PlaceForm } from '#lib/api/forms.ts';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, fetch }) => {
	const [options, place] = await Promise.all([loadOptions(fetch), loadForm<PlaceForm>(fetch, 'places', params.id)]);
	return { options, place };
};

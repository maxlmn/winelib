import { loadForm, loadOptions } from '#lib/api/forms.ts';
import type { WineForm } from '#lib/api/forms.ts';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, fetch }) => {
	const [options, wine] = await Promise.all([loadOptions(fetch), loadForm<WineForm>(fetch, 'wines', params.id)]);
	return { options, wine };
};

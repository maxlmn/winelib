import { loadOptional, loadOptions } from '#lib/api/forms.ts';
import type { WineForm } from '#lib/api/forms.ts';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, url }) => {
	const [options, wine] = await Promise.all([
		loadOptions(fetch),
		loadOptional<WineForm>(fetch, 'wines', url.searchParams.get('wine_id'))
	]);
	return { options, wine: wine?.summary ?? null };
};

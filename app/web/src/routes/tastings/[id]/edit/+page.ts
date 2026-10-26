import { loadForm, loadOptions } from '#lib/api/forms.ts';
import type { TastingForm } from '#lib/api/forms.ts';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, fetch }) => {
	const [options, tasting] = await Promise.all([loadOptions(fetch), loadForm<TastingForm>(fetch, 'tastings', params.id)]);
	return { options, tasting };
};

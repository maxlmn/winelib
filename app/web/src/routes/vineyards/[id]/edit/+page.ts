import { loadForm, loadOptions } from '#lib/api/forms.ts';
import type { VineyardForm } from '#lib/api/forms.ts';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, fetch }) => {
	const [options, vineyard] = await Promise.all([loadOptions(fetch), loadForm<VineyardForm>(fetch, 'vineyards', params.id)]);
	return { options, vineyard };
};

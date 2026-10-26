import { loadForm, loadOptions } from '#lib/api/forms.ts';
import type { AppellationForm } from '#lib/api/forms.ts';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, fetch }) => {
	const [options, appellation] = await Promise.all([loadOptions(fetch), loadForm<AppellationForm>(fetch, 'appellations', params.id)]);
	return { options, appellation };
};

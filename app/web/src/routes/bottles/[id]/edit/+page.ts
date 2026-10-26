import { loadForm, loadOptions } from '#lib/api/forms.ts';
import type { BottleForm } from '#lib/api/forms.ts';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, fetch }) => {
	const [options, bottle] = await Promise.all([loadOptions(fetch), loadForm<BottleForm>(fetch, 'bottles', params.id)]);
	return { options, bottle };
};

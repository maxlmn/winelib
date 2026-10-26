import { loadForm, loadOptions } from '#lib/api/forms.ts';
import type { ProducerForm } from '#lib/api/forms.ts';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, fetch }) => {
	const [options, producer] = await Promise.all([loadOptions(fetch), loadForm<ProducerForm>(fetch, 'producers', params.id)]);
	return { options, producer };
};

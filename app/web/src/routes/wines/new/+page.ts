import { loadOptional, loadOptions } from '#lib/api/forms.ts';
import type { ProducerForm } from '#lib/api/forms.ts';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, url }) => {
	const [options, producer] = await Promise.all([
		loadOptions(fetch),
		loadOptional<ProducerForm>(fetch, 'producers', url.searchParams.get('producer_id'))
	]);
	return { options, producer };
};

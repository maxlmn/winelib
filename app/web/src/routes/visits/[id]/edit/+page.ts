import { loadForm, loadOptions } from '#lib/api/forms.ts';
import type { VisitForm } from '#lib/api/forms.ts';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, fetch }) => {
	const [options, visit] = await Promise.all([loadOptions(fetch), loadForm<VisitForm>(fetch, 'visits', params.id)]);
	return { options, visit };
};

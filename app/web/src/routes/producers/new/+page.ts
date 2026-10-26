import { loadOptions } from '#lib/api/forms.ts';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => ({ options: await loadOptions(fetch) });

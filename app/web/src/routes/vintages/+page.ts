import { loadVintages } from '#lib/api/details.ts';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => ({ vintages: await loadVintages(fetch) });

import { loadAppellation } from '#lib/api/details.ts';
import type { PageLoad } from './$types';

export const load: PageLoad = ({ fetch, params }) => loadAppellation(fetch, params.id);

import { loadRegion } from '#lib/api/details.ts';
import type { PageLoad } from './$types';

export const load: PageLoad = ({ fetch, params }) => loadRegion(fetch, params.id);

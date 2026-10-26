import { loadVintage } from '#lib/api/details.ts';
import type { PageLoad } from './$types';

export const load: PageLoad = ({ fetch, params }) => loadVintage(fetch, params.year);

import { loadVineyard } from '#lib/api/details.ts';
import type { PageLoad } from './$types';

export const load: PageLoad = ({ fetch, params }) => loadVineyard(fetch, params.id);

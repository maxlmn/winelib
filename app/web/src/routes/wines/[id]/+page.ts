import { loadWine } from '#lib/api/details.ts';
import type { PageLoad } from './$types';

export const load: PageLoad = ({ fetch, params }) => loadWine(fetch, params.id);

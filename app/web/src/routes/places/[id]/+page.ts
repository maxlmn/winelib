import { loadPlace } from '#lib/api/details.ts';
import type { PageLoad } from './$types';

export const load: PageLoad = ({ fetch, params }) => loadPlace(fetch, params.id);

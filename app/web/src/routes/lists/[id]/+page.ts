import { loadList } from '#lib/api/lists.ts';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, params }) => ({ list: await loadList(fetch, params.id) });

import { loadLists } from '#lib/api/lists.ts';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => ({ lists: await loadLists(fetch) });

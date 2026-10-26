import { getGrapes } from '#lib/api/grapes.ts';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => ({ grapes: await getGrapes(fetch) });

import { getPlaces } from '#lib/api/directory.ts';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => ({ places: await getPlaces(fetch) });

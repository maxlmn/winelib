import { getProducers } from '#lib/api/directory.ts';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => ({ producers: await getProducers(fetch) });

import { getAboutData } from '#lib/api/about.ts';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => ({ about: await getAboutData(fetch) });

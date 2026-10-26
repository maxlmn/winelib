import { getGuides } from '#lib/api/help.ts';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => ({ guides: await getGuides(fetch) });

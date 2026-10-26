import { getCellarSummary, getTastingSummary } from '#lib/api/summary.ts';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
	const [tastings, cellar] = await Promise.all([getTastingSummary(fetch), getCellarSummary(fetch)]);
	return { tastings, cellar };
};

import { loadOptions } from '#lib/api/forms.ts';
import { loadWishlist } from '#lib/api/wishlist.ts';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
	const [items, options] = await Promise.all([loadWishlist(fetch), loadOptions(fetch)]);
	return { items, options };
};

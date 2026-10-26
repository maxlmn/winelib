/** The filters and views live in the page's address, so any of them can be bookmarked or shared. */
import { goto } from '$app/navigation';
import { page } from '$app/state';

/** Changes the page's query: a value replaces the key's, a list its values; null, '' or [] removes it. `base` is the
 * query to start from (the current one by default). Replaces the history entry: filtering shouldn't flood the back
 * button. */
export function setParams(changes: Record<string, string | string[] | null>, base = new URLSearchParams(page.url.searchParams.toString())) {
	for (const [k, v] of Object.entries(changes)) {
		base.delete(k);
		if (Array.isArray(v)) v.forEach((x) => base.append(k, x));
		else if (v) base.set(k, v);
	}
	goto(`?${base}`, { replace: true, reset: false });
}

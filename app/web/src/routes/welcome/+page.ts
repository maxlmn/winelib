import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => ({
	critics: await fetch('/api/lookups/critics').then((r) => (r.ok ? (r.json() as Promise<string[]>) : []))
});

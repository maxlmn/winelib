import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
	const [options, critics] = await Promise.all([
		fetch('/api/lookups/options').then((r) => r.json() as Promise<{ locations: string[] }>),
		fetch('/api/lookups/critics').then((r) => (r.ok ? (r.json() as Promise<string[]>) : []))
	]);
	return { locations: options.locations, critics };
};

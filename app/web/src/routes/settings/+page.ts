import type { PageLoad } from './$types';
import type { AttentionItem } from '#lib/components/settings/Attention.svelte';

export const load: PageLoad = async ({ fetch }) => {
	const [options, critics, attention] = await Promise.all([
		fetch('/api/lookups/options').then((r) => r.json() as Promise<{ locations: string[] }>),
		fetch('/api/lookups/critics').then((r) => (r.ok ? (r.json() as Promise<string[]>) : [])),
		// the Needs attention tab and its count: the page shows without it when it fails
		fetch('/api/attention')
			.then((r) => (r.ok ? (r.json() as Promise<{ items: AttentionItem[] }>) : { items: [] }))
			.catch(() => ({ items: [] as AttentionItem[] }))
	]);
	return { locations: options.locations, critics, attention: attention.items };
};

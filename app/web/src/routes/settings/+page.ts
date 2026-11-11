import type { PageLoad } from './$types';
import type { AttentionItem } from '#lib/components/settings/Attention.svelte';

export const load: PageLoad = async ({ fetch }) => {
	// the Needs attention tab and its count: its checks take a few seconds on a large cellar, so the page doesn't wait
	// for them (a promise, filled in when they're done); the page shows without them when they fail
	const attention = fetch('/api/attention')
		.then((r) => (r.ok ? (r.json() as Promise<{ items: AttentionItem[] }>) : { items: [] }))
		.then((a) => a.items)
		.catch(() => [] as AttentionItem[]);
	const [options, critics] = await Promise.all([
		fetch('/api/lookups/options').then((r) => r.json() as Promise<{ locations: string[] }>),
		fetch('/api/lookups/critics').then((r) => (r.ok ? (r.json() as Promise<string[]>) : []))
	]);
	// the version it runs (not awaited either; nothing shown when it isn't said: the demo)
	const version = fetch('/api/health')
		.then((r) => (r.ok ? (r.json() as Promise<{ version?: string }>) : {}))
		.then((h: { version?: string }) => h.version ?? null)
		.catch(() => null);
	return { locations: options.locations, critics, attention, version };
};

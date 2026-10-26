import { redirect } from '@sveltejs/kit';
import { loadSettings } from '#lib/settings.svelte.ts';
import { loadRegionCountries } from '#lib/regions.svelte.ts';
import type { LayoutLoad } from './$types';

// Client-rendered SPA: data comes from the FastAPI backend
export const ssr = false;
export const prerender = false;

// Settings and regions are loaded once per visit (pages that change them update the stores); the setup check runs
// until it passes
let loaded: Promise<unknown> | null = null;
let setUp = false;

export const load: LayoutLoad = async ({ fetch, url, untrack }) => {
	loaded ??= Promise.all([loadSettings(fetch), loadRegionCountries(fetch)]);
	await loaded;
	// A new installation: the first-start page until its settings are saved once
	if (!setUp && untrack(() => url.pathname) !== '/welcome') {
		const setup = await fetch('/api/settings/setup').then((r) => (r.ok ? r.json() : null)).catch(() => null);
		if (setup?.needed) redirect(307, '/welcome');
		setUp = true;
	}
	return {};
};

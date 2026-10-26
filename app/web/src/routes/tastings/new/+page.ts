import { loadOptional, loadOptions } from '#lib/api/forms.ts';
import type { BottleForm, BottleOption, PlaceOption, WineForm } from '#lib/api/forms.ts';
import type { TastingPrefill } from '#lib/components/forms/TastingEditor.svelte';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, url }) => {
	const q = url.searchParams;
	const wineId = q.get('wine_id');
	const [options, bottle, wine, place, stocked] = await Promise.all([
		loadOptions(fetch),
		loadOptional<BottleForm>(fetch, 'bottles', q.get('bottle_id')),
		loadOptional<WineForm>(fetch, 'wines', wineId),
		loadOptional<PlaceOption>(fetch, 'places', q.get('place_id')),
		wineId && /^\d+$/.test(wineId)
			? fetch(`/api/lookups/bottles?wine_id=${wineId}`).then((r) => (r.ok ? (r.json() as Promise<BottleOption[]>) : []))
			: []
	]);
	const date = q.get('date');
	const prefill: TastingPrefill = {
		// Drinking a given bottle, or one in stock of the given wine; otherwise the wine is picked as "other wine"
		bottle: bottle?.option ?? stocked[0] ?? null,
		wine: wine?.summary ?? null,
		place,
		date: date && /^\d{4}-\d{2}-\d{2}$/.test(date) ? date : null
	};
	return { options, prefill };
};

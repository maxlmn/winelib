/** Regions are named with their country wherever they show: "Mosel, Germany", "Victoria, Australia"; a
 * country-level region (Italy) as it is. With their colour as a reminder (RegionName). The countries and
 * colours are loaded once by the root layout. */
import { FALLBACK_REGION } from './colors.ts';

type Fetch = typeof fetch;

// region name -> its country, for the regions whose name isn't the country's
export const regionCountries = $state<Record<string, string>>({});
// region name -> its colour
export const regionColorsByName = $state<Record<string, string>>({});

export async function loadRegionCountries(fetch: Fetch) {
	const get = (url: string) => fetch(url).then((r) => (r.ok ? r.json() : {})).catch(() => ({}));
	const [countries, colors] = await Promise.all([get('/api/region-countries'), get('/api/regions')]);
	Object.assign(regionCountries, countries);
	Object.assign(regionColorsByName, colors);
}

/** "Mosel, Germany"; the name alone for a country-level region, an unknown one or none. */
export function regionLabel(name: string | null | undefined): string {
	if (!name) return name ?? '';
	const country = regionCountries[name];
	return country ? `${name}, ${country}` : name;
}

/** The region's colour (the neutral one when it has none), or null without a region. */
export function regionColor(name: string | null | undefined): string | null {
	return name ? (regionColorsByName[name] ?? FALLBACK_REGION) : null;
}

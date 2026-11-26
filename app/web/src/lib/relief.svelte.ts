/** Relief on the Plain map (hillshading from Mapterhorn's terrain tiles, basemap.ts): a per-browser choice, on unless
 * turned off; every open map follows it at once (also those without an effect of their own: PointMap, the place
 * picker). */
import { persistedFlag } from '#lib/flag.svelte.ts';

const flag = persistedFlag('winelib-relief');
export const relief = flag.state;

const listeners = new Set<(on: boolean) => void>();

/** Called by each map (basemap.ts) when the choice changes; returns the unsubscribe */
export function onRelief(fn: (on: boolean) => void) {
	listeners.add(fn);
	return () => listeners.delete(fn);
}

export function setRelief(on: boolean) {
	flag.set(on);
	for (const fn of listeners) fn(on);
}

/** The Relief button beside Plain / Satellite (a detail page's map, the Map page): pressed only where it shows */
export function reliefButton(basemap: string) {
	const plain = basemap === 'plain';
	return {
		pressed: plain && relief.on,
		disabled: !plain,
		title: plain ? 'The hills shaded on the map' : 'Relief shows on the Plain map'
	};
}

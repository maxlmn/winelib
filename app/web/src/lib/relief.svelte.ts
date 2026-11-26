/** Relief on the Plain map (hillshading from Mapterhorn's terrain tiles, basemap.ts): a per-browser choice, on unless
 * turned off; every open map follows it at once. */

const KEY = 'winelib-relief';

function saved() {
	try {
		return localStorage.getItem(KEY) !== 'off';
	} catch {
		return true;
	}
}

export const relief = $state({ on: typeof localStorage === 'undefined' ? true : saved() });

const listeners = new Set<(on: boolean) => void>();

/** Called by each map (basemap.ts) when the choice changes; returns the unsubscribe */
export function onRelief(fn: (on: boolean) => void) {
	listeners.add(fn);
	return () => listeners.delete(fn);
}

export function setRelief(on: boolean) {
	relief.on = on;
	try {
		localStorage.setItem(KEY, on ? 'on' : 'off');
	} catch {
		/* private window: kept for this visit only */
	}
	for (const fn of listeners) fn(on);
}

/** Contour lines inside the vineyards on the maps (GET /api/map/vineyard-contours: worked out with each vineyard's
 * relief, relief.py): a per-browser choice, on unless turned off from a map's legend. */
const KEY = 'winelib-contours';

function saved() {
	try {
		return localStorage.getItem(KEY) !== 'off';
	} catch {
		return true;
	}
}

export const contours = $state({ on: typeof localStorage === 'undefined' ? true : saved() });

export function setContours(on: boolean) {
	contours.on = on;
	try {
		localStorage.setItem(KEY, on ? 'on' : 'off');
	} catch {
		/* private window: for this visit only */
	}
}

/** Contour lines and slope shading inside the vineyards on the maps (mapContours.ts): a per-browser choice, on unless
 * turned off from a map's legend; `rev` moves when a vineyard's relief has just been worked out (its page's first
 * visit), so the maps showing it ask for its contours again. */
import { persistedFlag } from '#lib/flag.svelte.ts';
import { forgetContours } from '#lib/mapContours.ts';

const flag = persistedFlag('winelib-contours');
export const contours = flag.state;
export const contourRev = $state({ rev: 0 });

export const setContours = (on: boolean) => flag.set(on);

/** A vineyard's relief was just worked out (or again, its outline redrawn): its contours asked for afresh */
export function reliefWorkedOut(vineyardId: number) {
	forgetContours(vineyardId);
	contourRev.rev++;
}

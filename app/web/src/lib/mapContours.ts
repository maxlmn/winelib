/** The contour lines and height bands inside the vineyards on a map (WineMap): their layers, their colours (the
 * theme's), and the data, asked for per vineyard and kept (GET /api/map/vineyard-contours, routers/relief.py): a map
 * whose vineyards arrive in batches (the Map page) asks only for the new ones, a hundred at a time. */
import type { Map as MlMap, GeoJSONSource } from 'maplibre-gl';
import type { Feature, FeatureCollection } from 'geojson';
import { request } from '#lib/api/http.ts';

const SOURCE = 'vine-contours';
const BATCH = 100;
const EMPTY: FeatureCollection = { type: 'FeatureCollection', features: [] };

/** The source and its layers, under `before` (the vineyards' outlines): the bands shading the slope from its foot
 * (a shadow) to its top (a little light), the lines, their height along them when close */
export function addContourLayers(map: MlMap, before: string) {
	map.addSource(SOURCE, { type: 'geojson', data: EMPTY });
	map.addLayer({
		id: 'vines-band', type: 'fill', source: SOURCE, filter: ['==', ['get', 'kind'], 'band'],
		paint: {
			'fill-color': ['interpolate', ['linear'], ['get', 't'], 0, 'rgba(20, 10, 5, 0.4)', 0.5, 'rgba(20, 10, 5, 0.12)', 1, 'rgba(255, 250, 240, 0.2)'],
			'fill-antialias': false
		}
	}, before);
	map.addLayer({
		id: 'vines-contour', type: 'line', source: SOURCE, filter: ['==', ['get', 'kind'], 'line'],
		layout: { 'line-join': 'round', 'line-cap': 'round' },
		paint: { 'line-width': ['interpolate', ['linear'], ['zoom'], 12, 0.5, 16, 1.2] }
	}, before);
	map.addLayer({
		id: 'vines-contour-label', type: 'symbol', source: SOURCE, minzoom: 14.5, filter: ['==', ['get', 'kind'], 'line'],
		layout: { 'symbol-placement': 'line', 'symbol-spacing': 300, 'text-field': ['concat', ['to-string', ['get', 'ele']], ' m'], 'text-font': ['Noto Sans Regular'], 'text-size': 9.5 },
		paint: { 'text-halo-width': 1.2 }
	}, before);
}

/** Colours for the theme; shown with the contours on: the bands on filled vineyards only (an outline-only vineyard
 * keeps its ground clear), the lines on any shown vineyard */
export function paintContours(map: MlMap, dark: boolean, vineyards: 'fill' | 'outline' | 'off', on: boolean) {
	if (!map.getLayer('vines-contour')) return;
	map.setPaintProperty('vines-contour', 'line-color', dark ? 'rgba(255, 245, 235, 0.55)' : 'rgba(40, 25, 15, 0.55)');
	map.setPaintProperty('vines-contour-label', 'text-color', dark ? '#f3ece6' : '#3a2a20');
	map.setPaintProperty('vines-contour-label', 'text-halo-color', dark ? 'rgba(20, 18, 22, 0.85)' : 'rgba(255, 255, 255, 0.85)');
	const show = (id: string, yes: boolean) => map.setLayoutProperty(id, 'visibility', yes ? 'visible' : 'none');
	show('vines-band', on && vineyards === 'fill');
	show('vines-contour', on && vineyards !== 'off');
	show('vines-contour-label', on && vineyards !== 'off');
}

export function setContourData(map: MlMap, fc: FeatureCollection | null) {
	(map.getSource(SOURCE) as GeoJSONSource | undefined)?.setData(fc ?? EMPTY);
}

// per vineyard id: its features (none: asked, nothing worked out yet)
const cache = new Map<number, Feature[]>();

export const forgetContours = (id: number) => cache.delete(id);

/** The contours of some vineyards: those not kept asked for (sorted, a hundred at a time), all of them returned */
export async function contoursOf(ids: number[], signal?: AbortSignal): Promise<FeatureCollection> {
	const wanted = [...new Set(ids)].filter((id) => !cache.has(id)).sort((a, b) => a - b);
	for (let i = 0; i < wanted.length; i += BATCH) {
		const batch = wanted.slice(i, i + BATCH);
		const fc = await request<FeatureCollection>(`/api/map/vineyard-contours?ids=${batch.join(',')}`, { signal });
		const by = new Map<number, Feature[]>(batch.map((id) => [id, []]));
		for (const f of fc.features) by.get(Number(f.properties?.vineyard))?.push(f);
		for (const [id, fs] of by) cache.set(id, fs);
	}
	return { type: 'FeatureCollection', features: ids.flatMap((id) => cache.get(id) ?? []) };
}

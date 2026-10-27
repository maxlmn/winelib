import type { Map as MlMap, RasterLayerSpecification, RasterTileSource } from 'maplibre-gl';
// MapLibre resolves its worker next to its own module, which bundling breaks: point it at Vite's copy
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url';

export type Basemap = 'plain' | 'topo' | 'satellite';

export function basemapTiles(kind: Basemap): { tiles: string[]; attribution: string } {
	if (kind === 'satellite')
		return {
			tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'],
			attribution: '© Esri, Maxar, Earthstar Geographics'
		};
	if (kind === 'topo')
		return {
			tiles: ['a', 'b', 'c'].map((s) => `https://${s}.tile.opentopomap.org/{z}/{x}/{y}.png`),
			attribution: '© OpenStreetMap · © OpenTopoMap (CC-BY-SA)'
		};
	// Plain: OpenStreetMap France (CARTO's tiles now want an API key),
	// toned down by basemapPaint so the boundaries stand out
	return {
		tiles: ['a', 'b', 'c'].map((s) => `https://${s}.tile.openstreetmap.fr/osmfr/{z}/{x}/{y}.png`),
		attribution: '© OpenStreetMap France · © OpenStreetMap contributors'
	};
}

type RasterPaint = NonNullable<RasterLayerSpecification['paint']>;

/** Plain is a muted OpenStreetMap: mostly grey in light mode, inverted (min > max) and hue-turned back in dark mode. */
export function basemapPaint(kind: Basemap, dark: boolean): RasterPaint {
	if (kind !== 'plain') return { 'raster-saturation': 0, 'raster-brightness-min': 0, 'raster-brightness-max': 1, 'raster-hue-rotate': 0, 'raster-contrast': 0 };
	return dark
		? { 'raster-saturation': -0.75, 'raster-brightness-min': 0.85, 'raster-brightness-max': 0.08, 'raster-hue-rotate': 180, 'raster-contrast': 0.1 }
		: { 'raster-saturation': -0.8, 'raster-brightness-min': 0.12, 'raster-brightness-max': 1, 'raster-hue-rotate': 0, 'raster-contrast': -0.1 };
}

/** Switches an existing map's basemap (tiles and tone). */
export function setBasemap(map: MlMap, kind: Basemap, dark: boolean) {
	(map.getSource('base') as RasterTileSource).setTiles(basemapTiles(kind).tiles);
	for (const [k, v] of Object.entries(basemapPaint(kind, dark))) map.setPaintProperty('base', k as keyof RasterPaint, v);
}

/** The resolved app theme (see theme.svelte.ts), not just the OS preference. */
export const isDark = () => document.documentElement.dataset.theme === 'dark';

/** A MapLibre map with the raster basemap and zoom controls; resolves once the style has loaded. */
/** A map on a basemap, opened at a view: a centre and zoom, or `bounds` to fit (opening there at once, rather than
 * loading one place's tiles to move elsewhere). Resolves once its style is there (sources and layers can be added),
 * not after the first tiles: they stream in while the caller draws */
export async function createMap(
	container: HTMLElement,
	basemap: Basemap,
	view: { center: [number, number]; zoom: number } | { bounds: [number, number, number, number]; fitBoundsOptions?: { padding: number } } = {
		center: [4.5, 46.5],
		zoom: 5
	}
) {
	const maplibre = await import('maplibre-gl');
	maplibre.setWorkerUrl(workerUrl);
	const map = new maplibre.Map({
		container,
		style: {
			version: 8,
			sources: { base: { type: 'raster', tileSize: 256, maxzoom: 19, ...basemapTiles(basemap) } },
			layers: [{ id: 'base', type: 'raster', source: 'base', paint: basemapPaint(basemap, isDark()) }]
		},
		...view
	});
	map.addControl(new maplibre.NavigationControl({ showCompass: false }), 'top-right');
	map.addControl(new maplibre.ScaleControl({}), 'bottom-left');
	await new Promise<void>((resolve) => map.once('style.load', () => resolve()));
	return map as MlMap;
}

import type { LayerSpecification, Map as MlMap, RasterLayerSpecification, RasterTileSource } from 'maplibre-gl';
import { GLYPHS, VECTOR_IDS, VECTOR_SOURCE, vectorLayers, vectorPaint } from '#lib/vectorBase.ts';
// MapLibre resolves its worker next to its own module, which bundling breaks: point it at Vite's copy
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url';

export type Basemap = 'plain' | 'satellite';

/** The raster basemaps' tiles. Plain is drawn from vector tiles (vectorBase.ts); OpenStreetMap France's raster tiles
 * are its fallback when OpenFreeMap can't be reached. */
function basemapTiles(kind: Basemap): { tiles: string[]; attribution: string } {
	if (kind === 'satellite')
		return { tiles: ['sat://{z}/{x}/{y}'], attribution: '© IGN — BD ORTHO (France) · © Esri, Maxar, Earthstar Geographics' };
	return {
		tiles: ['a', 'b', 'c'].map((s) => `https://${s}.tile.openstreetmap.fr/osmfr/{z}/{x}/{y}.png`),
		attribution: '© OpenStreetMap France · © OpenStreetMap contributors'
	};
}

type RasterPaint = NonNullable<RasterLayerSpecification['paint']>;

/** The raster fallback for Plain is a muted OpenStreetMap: mostly grey in light mode, inverted (min > max) and
 * hue-turned back in dark mode. */
function basemapPaint(kind: Basemap, dark: boolean): RasterPaint {
	if (kind !== 'plain') return { 'raster-saturation': 0, 'raster-brightness-min': 0, 'raster-brightness-max': 1, 'raster-hue-rotate': 0, 'raster-contrast': 0 };
	return dark
		? { 'raster-saturation': -0.75, 'raster-brightness-min': 0.85, 'raster-brightness-max': 0.08, 'raster-hue-rotate': 180, 'raster-contrast': 0.1 }
		: { 'raster-saturation': -0.8, 'raster-brightness-min': 0.12, 'raster-brightness-max': 1, 'raster-hue-rotate': 0, 'raster-contrast': -0.1 };
}

// Satellite: IGN's aerial photos in France (BD ORTHO, sharper and newer than Esri's), Esri's elsewhere, through one
// `sat://` source that asks for one tile per place: IGN's where it covers (as it comes: most tiles), Esri's outside
// its box, and at a border (IGN's tile partly blank white) Esri's under IGN's, the white made see-through.
const IGN_BOUNDS: [number, number, number, number] = [-5.3, 41.3, 9.7, 51.2];
const IGN_URL = (z: string, x: string, y: string) =>
	'https://data.geopf.fr/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=ORTHOIMAGERY.ORTHOPHOTOS&STYLE=normal' +
	`&TILEMATRIXSET=PM&FORMAT=image/jpeg&TILEMATRIX=${z}&TILECOL=${x}&TILEROW=${y}`;
const ESRI_URL = (z: string, x: string, y: string) =>
	`https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/${z}/${y}/${x}`;

/** A tile's box (west, south, east, north) */
function tileBox(z: number, x: number, y: number): [number, number, number, number] {
	const n = 2 ** z;
	const lat = (t: number) => (Math.atan(Math.sinh(Math.PI * (1 - (2 * t) / n))) * 180) / Math.PI;
	return [(x / n) * 360 - 180, lat(y + 1), ((x + 1) / n) * 360 - 180, lat(y)];
}

async function bytesOf(url: string, abort: AbortController) {
	const res = await fetch(url, { signal: abort.signal });
	if (!res.ok) throw new Error(`tile ${res.status}`);
	return res.arrayBuffer();
}

async function satTile(params: { url: string }, abort: AbortController) {
	const [z, x, y] = params.url.replace('sat://', '').split('/');
	const [w, s, e, n] = tileBox(+z, +x, +y);
	const [bw, bs, be, bn] = IGN_BOUNDS;
	const esri = () => bytesOf(ESRI_URL(z, x, y), abort);
	if (e < bw || w > be || n < bs || s > bn) return { data: await esri() };
	const res = await fetch(IGN_URL(z, x, y), { signal: abort.signal });
	if (res.status === 404) return { data: await esri() }; // none there (beyond IGN's photos)
	if (!res.ok) throw new Error(`IGN tile ${res.status}`);
	const bytes = await res.arrayBuffer();
	const bitmap = await createImageBitmap(new Blob([bytes]));
	const canvas = new OffscreenCanvas(bitmap.width, bitmap.height);
	const ctx = canvas.getContext('2d')!;
	ctx.drawImage(bitmap, 0, 0);
	const img = ctx.getImageData(0, 0, bitmap.width, bitmap.height);
	const px = img.data;
	let white = 0;
	for (let i = 0; i < px.length; i += 4) {
		if (px[i] > 249 && px[i + 1] > 249 && px[i + 2] > 249) {
			px[i + 3] = 0;
			white++;
		}
	}
	// a photo throughout (most tiles in France): as it came, nothing else asked for
	if (white < 64) return { data: bytes };
	const below = await esri();
	// blank throughout (just outside France): Esri's alone
	if (white >= px.length / 4 - 64) return { data: below };
	const under = await createImageBitmap(new Blob([below]));
	ctx.clearRect(0, 0, canvas.width, canvas.height);
	ctx.drawImage(under, 0, 0, canvas.width, canvas.height);
	const top = new OffscreenCanvas(canvas.width, canvas.height);
	top.getContext('2d')!.putImageData(img, 0, 0);
	ctx.drawImage(top, 0, 0);
	return { data: await (await canvas.convertToBlob({ type: 'image/jpeg', quality: 0.9 })).arrayBuffer() };
}
let satRegistered = false;

// Per map: the basemap shown, and whether OpenFreeMap failed (Plain then falls back to raster tiles)
const state = new WeakMap<MlMap, { kind: Basemap; dark: boolean; vectorDown: boolean }>();

/** Switches an existing map's basemap (which layers show, their tiles and tone). */
export function setBasemap(map: MlMap, kind: Basemap, dark: boolean) {
	const st = state.get(map) ?? { kind, dark, vectorDown: false };
	st.kind = kind;
	st.dark = dark;
	state.set(map, st);
	const vector = kind === 'plain' && !st.vectorDown;
	for (const id of VECTOR_IDS) map.setLayoutProperty(id, 'visibility', vector ? 'visible' : 'none');
	if (vector) for (const [id, k, v] of vectorPaint(dark)) map.setPaintProperty(id, k as keyof RasterPaint, v as number);
	map.setLayoutProperty('base', 'visibility', vector ? 'none' : 'visible');
	if (!vector) {
		(map.getSource('base') as RasterTileSource).setTiles(basemapTiles(kind).tiles);
		for (const [k, v] of Object.entries(basemapPaint(kind, dark))) map.setPaintProperty('base', k as keyof RasterPaint, v);
	}
}

/** The resolved app theme (see theme.svelte.ts), not just the OS preference. */
const isDark = () => document.documentElement.dataset.theme === 'dark';

/** A map on a basemap, opened at a view: a centre and zoom, or `bounds` to fit (opening there at once, rather than
 * loading one place's tiles to move elsewhere). Resolves once its style is there (sources and layers can be added),
 * not after the first tiles: they stream in while the caller draws */
export async function createMap(
	container: HTMLElement,
	basemap: Basemap,
	view: { center: [number, number]; zoom: number } | { bounds: [number, number, number, number]; fitBoundsOptions?: { padding: number | { top: number; right: number; bottom: number; left: number } } } = {
		center: [4.5, 46.5],
		zoom: 5
	}
) {
	const maplibre = await import('maplibre-gl');
	maplibre.setWorkerUrl(workerUrl);
	if (!satRegistered) {
		maplibre.addProtocol('sat', satTile);
		satRegistered = true;
	}
	const dark = isDark();
	const vector = basemap === 'plain';
	const shown = (on: boolean) => ({ visibility: on ? ('visible' as const) : ('none' as const) });
	const map = new maplibre.Map({
		container,
		style: {
			version: 8,
			glyphs: GLYPHS,
			sources: {
				ofm: { type: 'vector', url: VECTOR_SOURCE },
				base: { type: 'raster', tileSize: 256, maxzoom: 19, ...basemapTiles(basemap) }
			},
			layers: [
				...vectorLayers(dark).map((l) => ({ ...l, layout: { ...l.layout, ...shown(vector) } }) as LayerSpecification),
				{ id: 'base', type: 'raster', source: 'base', paint: basemapPaint(basemap, dark), layout: shown(!vector) }
			]
		},
		...view,
		attributionControl: false
	}) as unknown as MlMap;
	state.set(map, { kind: basemap, dark, vectorDown: false });
	// OpenFreeMap unreachable (its TileJSON or first tiles failing): Plain falls back to OpenStreetMap France's tiles
	let vectorTiles = false;
	map.on('sourcedata', (e) => {
		if (e.sourceId === 'ofm' && e.tile) vectorTiles = true;
	});
	map.on('error', (ev) => {
		const e = ev as unknown as { sourceId?: string };
		const st = state.get(map);
		if (e.sourceId !== 'ofm' || vectorTiles || !st || st.vectorDown) return;
		st.vectorDown = true;
		setBasemap(map, st.kind, st.dark);
	});
	map.addControl(new maplibre.NavigationControl({ showCompass: false }), 'top-right');
	map.addControl(new maplibre.ScaleControl({}), 'bottom-left');
	// The credits folded into an ⓘ: MapLibre opens them when they first arrive (with a source's data, after the style)
	// until the map is moved, so they're folded as soon as they're there; a tap opens them
	map.addControl(new maplibre.AttributionControl({ compact: true }), 'bottom-right');
	const fold = () => {
		const credits = container.querySelector('.maplibregl-ctrl-attrib');
		if (!credits?.classList.contains('maplibregl-compact')) return;
		credits.classList.remove('maplibregl-compact-show');
		map.off('sourcedata', fold);
	};
	map.on('sourcedata', fold);
	await new Promise<void>((resolve) => map.once('style.load', () => resolve()));
	return map;
}

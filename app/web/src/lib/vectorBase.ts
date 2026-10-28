import type { ExpressionSpecification, LayerSpecification } from 'maplibre-gl';

/** The Plain basemap: OpenFreeMap's vector tiles (OpenMapTiles' layers, OpenStreetMap's data, no key) drawn with our
 * own few layers, muted so the appellations and vineyards stand out: one palette for light, one for dark. */
export const VECTOR_SOURCE = 'https://tiles.openfreemap.org/planet';
export const GLYPHS = 'https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf';

const palettes = {
	light: {
		bg: '#f3f0eb', water: '#c8d5de', wood: '#dfe4d6', grass: '#e7e9dc', vines: '#ebe4d3', town: '#ebe7e2',
		building: '#dfdad4', minor: '#ffffff', major: '#fdfbf8', motorway: '#f3e7da', casing: '#d3cdc6',
		rail: '#c3bdb7', border: '#a99fa7', text: '#58525c', waterText: '#6a8394', halo: '#f3f0eb'
	},
	dark: {
		bg: '#232126', water: '#25313b', wood: '#283026', grass: '#2a2e26', vines: '#332d25', town: '#2a272c',
		building: '#343036', minor: '#3d3940', major: '#4b454e', motorway: '#5a4f57', casing: '#1b191d',
		rail: '#48424c', border: '#6e6574', text: '#bab2bd', waterText: '#7d95a6', halo: '#232126'
	}
};
type Palette = (typeof palettes)['light'];

const name: ExpressionSpecification = ['coalesce', ['get', 'name:latin'], ['get', 'name']];
const cls = (...c: string[]): ExpressionSpecification => ['match', ['get', 'class'], c, true, false];
const lines: ExpressionSpecification = ['match', ['geometry-type'], ['LineString', 'MultiLineString'], true, false];
const notTunnel: ExpressionSpecification = ['!=', ['get', 'brunnel'], 'tunnel'];
const zoomed = (stops: [number, number][]): ExpressionSpecification =>
	['interpolate', ['exponential', 1.5], ['zoom'], ...stops.flat()] as ExpressionSpecification;

const river = (wide: number, other: number): ExpressionSpecification => ['match', ['get', 'class'], 'river', wide, other];
// Road widths by zoom; a casing is the road and a line's width more on each side (zoom curves must stay top level)
const roadStops = {
	motorway: [[6, 0.6], [10, 1.6], [14, 5], [18, 18]] as [number, number][],
	major: [[7, 0.4], [10, 1], [14, 4], [18, 16]] as [number, number][],
	minor: [[12, 0.4], [14, 1.6], [18, 10]] as [number, number][]
};
const roadWidth = (k: keyof typeof roadStops) => zoomed(roadStops[k]);
const casing = (k: keyof typeof roadStops) => zoomed(roadStops[k].map(([z, w]) => [z, w + (z < 10 ? 0.6 : 1.6)]));

/** Each layer with its paint as a function of the palette (re-applied when the theme changes) */
const layers: { layer: { id: string; [k: string]: unknown }; paint: (p: Palette) => Record<string, unknown> }[] = [
	{ layer: { id: 'v-bg', type: 'background' }, paint: (p) => ({ 'background-color': p.bg }) },
	{ layer: { id: 'v-wood', type: 'fill', source: 'ofm', 'source-layer': 'landcover', filter: cls('wood', 'forest') }, paint: (p) => ({ 'fill-color': p.wood }) },
	{ layer: { id: 'v-grass', type: 'fill', source: 'ofm', 'source-layer': 'landcover', filter: cls('grass', 'wetland') }, paint: (p) => ({ 'fill-color': p.grass }) },
	{ layer: { id: 'v-vines', type: 'fill', source: 'ofm', 'source-layer': 'landcover', minzoom: 9, filter: ['==', ['get', 'subclass'], 'vineyard'] }, paint: (p) => ({ 'fill-color': p.vines }) },
	{ layer: { id: 'v-park', type: 'fill', source: 'ofm', 'source-layer': 'park' }, paint: (p) => ({ 'fill-color': p.grass, 'fill-opacity': 0.6 }) },
	{ layer: { id: 'v-town', type: 'fill', source: 'ofm', 'source-layer': 'landuse', filter: cls('residential', 'suburb', 'neighbourhood', 'commercial', 'industrial', 'retail') }, paint: (p) => ({ 'fill-color': p.town }) },
	{ layer: { id: 'v-water', type: 'fill', source: 'ofm', 'source-layer': 'water', filter: notTunnel }, paint: (p) => ({ 'fill-color': p.water }) },
	{ layer: { id: 'v-waterway', type: 'line', source: 'ofm', 'source-layer': 'waterway', filter: ['all', lines, notTunnel] }, paint: (p) => ({ 'line-color': p.water, 'line-width': ['interpolate', ['exponential', 1.5], ['zoom'], 8, river(0.6, 0), 12, river(1.6, 0.4), 16, river(5, 1.6)] }) },
	{ layer: { id: 'v-building', type: 'fill', source: 'ofm', 'source-layer': 'building', minzoom: 14 }, paint: (p) => ({ 'fill-color': p.building }) },
	{ layer: { id: 'v-path', type: 'line', source: 'ofm', 'source-layer': 'transportation', minzoom: 13, filter: ['all', lines, cls('path', 'track')] }, paint: (p) => ({ 'line-color': p.casing, 'line-width': 1, 'line-dasharray': [2, 1.5] }) },
	{ layer: { id: 'v-rail', type: 'line', source: 'ofm', 'source-layer': 'transportation', minzoom: 9, filter: ['all', lines, cls('rail'), notTunnel] }, paint: (p) => ({ 'line-color': p.rail, 'line-width': zoomed([[9, 0.5], [16, 2]]) }) },
	{ layer: { id: 'v-minor-casing', type: 'line', source: 'ofm', 'source-layer': 'transportation', minzoom: 13, filter: ['all', lines, cls('minor', 'service'), notTunnel], layout: { 'line-cap': 'round', 'line-join': 'round' } }, paint: (p) => ({ 'line-color': p.casing, 'line-width': casing('minor') }) },
	{ layer: { id: 'v-minor', type: 'line', source: 'ofm', 'source-layer': 'transportation', minzoom: 12, filter: ['all', lines, cls('minor', 'service'), notTunnel], layout: { 'line-cap': 'round', 'line-join': 'round' } }, paint: (p) => ({ 'line-color': p.minor, 'line-width': roadWidth('minor') }) },
	{ layer: { id: 'v-major-casing', type: 'line', source: 'ofm', 'source-layer': 'transportation', minzoom: 10, filter: ['all', lines, cls('primary', 'secondary', 'tertiary', 'trunk'), notTunnel], layout: { 'line-cap': 'round', 'line-join': 'round' } }, paint: (p) => ({ 'line-color': p.casing, 'line-width': casing('major') }) },
	{ layer: { id: 'v-major', type: 'line', source: 'ofm', 'source-layer': 'transportation', minzoom: 7, filter: ['all', lines, cls('primary', 'secondary', 'tertiary', 'trunk'), notTunnel], layout: { 'line-cap': 'round', 'line-join': 'round' } }, paint: (p) => ({ 'line-color': p.major, 'line-width': roadWidth('major') }) },
	{ layer: { id: 'v-motorway-casing', type: 'line', source: 'ofm', 'source-layer': 'transportation', minzoom: 8, filter: ['all', lines, cls('motorway'), notTunnel], layout: { 'line-cap': 'round', 'line-join': 'round' } }, paint: (p) => ({ 'line-color': p.casing, 'line-width': casing('motorway') }) },
	{ layer: { id: 'v-motorway', type: 'line', source: 'ofm', 'source-layer': 'transportation', minzoom: 5, filter: ['all', lines, cls('motorway'), notTunnel], layout: { 'line-cap': 'round', 'line-join': 'round' } }, paint: (p) => ({ 'line-color': p.motorway, 'line-width': roadWidth('motorway') }) },
	{ layer: { id: 'v-region', type: 'line', source: 'ofm', 'source-layer': 'boundary', minzoom: 4, filter: ['all', ['==', ['get', 'admin_level'], 4], ['!=', ['get', 'maritime'], 1]] }, paint: (p) => ({ 'line-color': p.border, 'line-width': zoomed([[4, 0.5], [10, 1.2]]), 'line-dasharray': [3, 2], 'line-opacity': 0.7 }) },
	{ layer: { id: 'v-country', type: 'line', source: 'ofm', 'source-layer': 'boundary', filter: ['all', ['==', ['get', 'admin_level'], 2], ['!=', ['get', 'maritime'], 1], ['!=', ['get', 'disputed'], 1]] }, paint: (p) => ({ 'line-color': p.border, 'line-width': zoomed([[2, 0.6], [10, 2]]) }) },
	{ layer: { id: 'v-water-name', type: 'symbol', source: 'ofm', 'source-layer': 'water_name', filter: ['match', ['geometry-type'], ['Point', 'MultiPoint'], true, false], layout: { 'text-field': name, 'text-font': ['Noto Sans Italic'], 'text-size': 12 } }, paint: (p) => ({ 'text-color': p.waterText, 'text-halo-color': p.halo, 'text-halo-width': 1.2 }) },
	{ layer: { id: 'v-river-name', type: 'symbol', source: 'ofm', 'source-layer': 'waterway', minzoom: 11, filter: ['all', lines, cls('river')], layout: { 'text-field': name, 'text-font': ['Noto Sans Italic'], 'text-size': 11, 'symbol-placement': 'line' } }, paint: (p) => ({ 'text-color': p.waterText, 'text-halo-color': p.halo, 'text-halo-width': 1.2 }) },
	{ layer: { id: 'v-road-name', type: 'symbol', source: 'ofm', 'source-layer': 'transportation_name', minzoom: 14, filter: ['all', lines, cls('primary', 'secondary', 'tertiary', 'minor')], layout: { 'text-field': name, 'text-font': ['Noto Sans Regular'], 'text-size': 10, 'symbol-placement': 'line' } }, paint: (p) => ({ 'text-color': p.text, 'text-halo-color': p.halo, 'text-halo-width': 1.2 }) },
	{ layer: { id: 'v-hamlet', type: 'symbol', source: 'ofm', 'source-layer': 'place', minzoom: 13, filter: cls('hamlet', 'isolated_dwelling', 'locality'), layout: { 'text-field': name, 'text-font': ['Noto Sans Regular'], 'text-size': 10 } }, paint: (p) => ({ 'text-color': p.text, 'text-halo-color': p.halo, 'text-halo-width': 1.2, 'text-opacity': 0.8 }) },
	{ layer: { id: 'v-village', type: 'symbol', source: 'ofm', 'source-layer': 'place', minzoom: 10, filter: cls('village'), layout: { 'text-field': name, 'text-font': ['Noto Sans Regular'], 'text-size': zoomed([[10, 10], [15, 13]]) } }, paint: (p) => ({ 'text-color': p.text, 'text-halo-color': p.halo, 'text-halo-width': 1.4 }) },
	{ layer: { id: 'v-town-name', type: 'symbol', source: 'ofm', 'source-layer': 'place', minzoom: 7, filter: cls('town'), layout: { 'text-field': name, 'text-font': ['Noto Sans Regular'], 'text-size': zoomed([[7, 10], [14, 15]]) } }, paint: (p) => ({ 'text-color': p.text, 'text-halo-color': p.halo, 'text-halo-width': 1.4 }) },
	{ layer: { id: 'v-city', type: 'symbol', source: 'ofm', 'source-layer': 'place', minzoom: 4, filter: cls('city'), layout: { 'text-field': name, 'text-font': ['Noto Sans Bold'], 'text-size': zoomed([[4, 10], [12, 17]]) } }, paint: (p) => ({ 'text-color': p.text, 'text-halo-color': p.halo, 'text-halo-width': 1.5 }) },
	{ layer: { id: 'v-country-name', type: 'symbol', source: 'ofm', 'source-layer': 'place', maxzoom: 7, filter: cls('country'), layout: { 'text-field': name, 'text-font': ['Noto Sans Bold'], 'text-size': zoomed([[2, 10], [6, 14]]), 'text-transform': 'uppercase', 'text-letter-spacing': 0.1 } }, paint: (p) => ({ 'text-color': p.text, 'text-halo-color': p.halo, 'text-halo-width': 1.5, 'text-opacity': 0.75 }) }
];

export const VECTOR_IDS = layers.map((l) => l.layer.id);

export function vectorLayers(dark: boolean): LayerSpecification[] {
	const p = dark ? palettes.dark : palettes.light;
	return layers.map(({ layer, paint }) => ({ ...layer, paint: paint(p) }) as unknown as LayerSpecification);
}

/** Each layer's paint for the theme (the palette changes, not the layers) */
export function vectorPaint(dark: boolean): [string, string, unknown][] {
	const p = dark ? palettes.dark : palettes.light;
	return layers.flatMap(({ layer, paint }) => Object.entries(paint(p)).map(([k, v]) => [layer.id, k, v] as [string, string, unknown]));
}

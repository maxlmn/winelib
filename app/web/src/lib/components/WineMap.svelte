<script lang="ts" module>
	export type { Basemap } from '#lib/basemap.ts';
	export type Selection = { kind: 'appellation' | 'vineyard'; id: number } | null;
</script>

<script lang="ts">
	import { onMount } from 'svelte';
	import 'maplibre-gl/dist/maplibre-gl.css';
	import type { ExpressionSpecification, GeoJSONSource, Map as MlMap } from 'maplibre-gl';
	import type { MapCollection, MapProps, RegionProps } from '#lib/types.ts';
	import type { FeatureCollection, Geometry } from 'geojson';
	import { plural, money } from '#lib/format.ts';
	import { links } from '#lib/links.ts';
	import { bbox } from '#lib/geo.ts';
	import { FALLBACK_REGION } from '#lib/colors.ts';
	import type { Extent } from '#lib/geo.ts';
	import { createMap, setBasemap } from '#lib/basemap.ts';
	import { atLightness, cruShade } from '#lib/cru.ts';
	import { accentColor, theme } from '#lib/theme.svelte.ts';
	import type { Basemap } from '#lib/basemap.ts';

	interface Props {
		appellations: MapCollection | null;
		vineyards: MapCollection | null;
		showAppellations?: boolean;
		showVineyards?: boolean;
		selected: Selection;
		basemap: Basemap;
		/** fit the view whenever this changes (e.g. a new region)... */
		fitKey: string;
		/** ...to this extent, or to the drawn data when not given */
		extent?: Extent | null;
		onselect: (p: MapProps | null) => void;
		/** keep the selected feature's card open, with a link to its page */
		pinCard?: boolean;
		/** region outlines, under everything else */
		regions?: FeatureCollection<Geometry | null, RegionProps> | null;
		/** clicking a region outline (the overview); without it, outlines are context only */
		onregion?: ((r: RegionProps) => void) | null;
	}

	let {
		appellations, vineyards, showAppellations = true, showVineyards = true,
		selected, basemap, fitKey, extent = null, onselect, pinCard = true,
		regions = null, onregion = null
	}: Props = $props();

	// Vineyards are shaded by village from a family of vine-leaf greens, olives and teals: neighbouring
	// villages read apart while the whole stays one calm layer. All at one lightness (only the hue tells villages
	// apart), so a darker vineyard is always a premier or grand cru. [fill, edge] pairs.
	const VINE_LIGHTNESS = 0.48;
	const VINE_HUES = ['#3fa66b', '#2a9d8f', '#8cb369', '#5b8e3e', '#43aa8b', '#a7c957', '#279989', '#6fa35a', '#4f9d5d', '#9bbf5a'];
	const VINE_PALETTE: [string, string][] = VINE_HUES.map((c) => [atLightness(c, VINE_LIGHTNESS), atLightness(c, VINE_LIGHTNESS - 0.17)]);

	function hashIndex(text: string, n: number) {
		let h = 5381;
		for (let i = 0; i < text.length; i++) h = (h * 33) ^ text.charCodeAt(i);
		return Math.abs(h) % n;
	}

	// Premier crus one notch darker, grand crus two (vineyards and appellations alike)
	function shadeVineyards(fc: MapCollection): MapCollection {
		return {
			...fc,
			features: fc.features.map((f) => {
				const [fill, edge] = VINE_PALETTE[hashIndex(f.properties.village ?? f.properties.name, VINE_PALETTE.length)];
				const cru = f.properties.cru;
				return { ...f, properties: { ...f.properties, fill: cruShade(fill, cru), edge: cruShade(edge, cru) } };
			})
		};
	}

	/** Crus take a shade of their region's color. An appellation spanning others ("Bourgogne" around its villages:
	 * its box holds the centres of 3 or more) is an umbrella: drawn first and as an outline, so the detail shows */
	function shadeAppellations(fc: MapCollection): MapCollection {
		const boxes = fc.features.map((f) => bbox([f.geometry]));
		const centres = boxes.map((b) => b && [(b[0] + b[2]) / 2, (b[1] + b[3]) / 2]);
		const umbrella = boxes.map(
			(b, i) => !!b && centres.filter((c, j) => j !== i && c && c[0] >= b[0] && c[0] <= b[2] && c[1] >= b[1] && c[1] <= b[3]).length >= 3
		);
		const features = fc.features.map((f, i) => {
			const color = f.properties.cru ? cruShade(f.properties.color ?? FALLBACK_REGION, f.properties.cru) : f.properties.color;
			return { ...f, properties: { ...f.properties, color, umbrella: umbrella[i] } };
		});
		return { ...fc, features: [...features.filter((f) => f.properties.umbrella), ...features.filter((f) => !f.properties.umbrella)] };
	}
	const EMPTY: MapCollection = { type: 'FeatureCollection', features: [], missing: [] };

	let container: HTMLDivElement;
	let map = $state<MlMap>();
	let ready = $state(false);
	let hovered = $state<MapProps | null>(null);
	let hoveredRegion = $state<RegionProps | null>(null);
	let fitted = '';

	// The card shows what's under the pointer, else the selected feature (clickable, with its links)
	const pinned = $derived.by(() => {
		if (!pinCard || !selected) return null;
		const fc = selected.kind === 'appellation' ? appellations : vineyards;
		return fc?.features.find((f) => f.properties.id === selected.id)?.properties ?? null;
	});
	const card = $derived(hovered ?? pinned);
	const isPinned = $derived(!!card && card === pinned && !hovered);
	const detailsUrl = (p: MapProps) => (p.kind === 'appellation' ? links.appellation(p.id) : links.vineyard(p.id));

	/** Fly to one appellation or vineyard (to `fallback` while its shape isn't drawn yet). */
	export function focus(sel: NonNullable<Selection>, fallback?: Extent | null) {
		const fc = sel.kind === 'appellation' ? appellations : vineyards;
		const f = fc?.features.find((f) => f.properties.id === sel.id);
		const b = (f && bbox([f.geometry])) ?? fallback;
		if (b && map) map.fitBounds(b, { padding: 80, maxZoom: sel.kind === 'vineyard' ? 15 : 11, duration: 700 });
	}

	onMount(() => {
		let m: MlMap | undefined;
		(async () => {
			m = await createMap(container, basemap);
			{
				const mm = m;
				mm.addSource('regions', { type: 'geojson', data: EMPTY, promoteId: 'id' });
				mm.addSource('apps', { type: 'geojson', data: EMPTY, promoteId: 'id' });
				mm.addSource('vines', { type: 'geojson', data: EMPTY, promoteId: 'id' });
				const hover: ExpressionSpecification = ['boolean', ['feature-state', 'hover'], false];
				const sel: ExpressionSpecification = ['boolean', ['feature-state', 'selected'], false];

				// Region outlines, in each region's color, under everything else. Their opacity depends
				// on whether they're the overview (clickable) or a region's context (see below)
				mm.addLayer({
					id: 'regions-fill', type: 'fill', source: 'regions',
					paint: { 'fill-color': ['coalesce', ['get', 'color'], FALLBACK_REGION], 'fill-opacity': 0 }
				});
				mm.addLayer({
					id: 'regions-line', type: 'line', source: 'regions',
					paint: { 'line-color': ['coalesce', ['get', 'color'], FALLBACK_REGION], 'line-width': 1.5 }
				});

				mm.addLayer({
					id: 'apps-fill', type: 'fill', source: 'apps',
					paint: {
						'fill-color': ['coalesce', ['get', 'color'], FALLBACK_REGION],
						// Kept light so vineyards drawn inside stay readable; hover and selection lift it.
						// Your bottles and tastings aren't marked on the shapes (busy with many small ones): see the tooltip
						'fill-opacity': ['case', sel, 0.4, hover, 0.3, ['boolean', ['get', 'umbrella'], false], 0, 0.16]
					}
				});
				mm.addLayer({
					id: 'apps-line', type: 'line', source: 'apps',
					paint: {
						'line-color': ['case', sel, accentColor(), ['coalesce', ['get', 'color'], FALLBACK_REGION]],
						'line-width': ['case', sel, 3, 1.2]
					}
				});
				mm.addLayer({
					id: 'vines-fill', type: 'fill', source: 'vines',
					paint: {
						'fill-color': ['get', 'fill'],
						'fill-opacity': ['case', sel, 0.95, hover, 0.92, 0.8]
					}
				});
				mm.addLayer({
					id: 'vines-line', type: 'line', source: 'vines',
					paint: {
						'line-color': ['case', sel, accentColor(), ['get', 'edge']],
						'line-width': ['interpolate', ['linear'], ['zoom'], 9, ['case', sel, 2, 0.3], 15, ['case', sel, 3.5, 1.2]]
					}
				});

				let hoverRef: { source: string; id: number } | null = null;
				const setHover = (ref: typeof hoverRef) => {
					if (hoverRef) mm.setFeatureState(hoverRef, { hover: false });
					hoverRef = ref;
					if (ref) mm.setFeatureState(ref, { hover: true });
				};
				// Regions answer the pointer only on the overview, and only where no shape is drawn over them
				const topFeature = (point: { x: number; y: number }) =>
					mm.queryRenderedFeatures([point.x, point.y], {
						layers: onregion ? ['vines-fill', 'apps-fill', 'regions-fill'] : ['vines-fill', 'apps-fill']
					})[0];
				// Rendered features carry flattened properties: take the region's own
				const regionOf = (id: unknown) => regions?.features.find((r) => r.properties.id === id)?.properties ?? null;

				mm.on('mousemove', (e) => {
					const f = topFeature(e.point);
					setHover(f ? { source: f.source, id: f.id as number } : null);
					const isRegion = f?.source === 'regions';
					hovered = f && !isRegion ? (f.properties as MapProps) : null;
					hoveredRegion = isRegion ? regionOf(f.id) : null;
					mm.getCanvas().style.cursor = f ? 'pointer' : '';
				});
				mm.on('mouseout', () => {
					setHover(null);
					hovered = null;
					hoveredRegion = null;
				});
				mm.on('click', (e) => {
					const f = topFeature(e.point);
					if (f?.source === 'regions') {
						const r = regionOf(f.id);
						if (r && onregion) onregion(r);
					} else onselect(f ? (f.properties as MapProps) : null);
				});
				map = mm;
				ready = true;
			}
		})();
		return () => m?.remove();
	});

	// Region outlines: the overview's are filled and clickable; inside a region, an outline for context
	$effect(() => {
		if (!ready || !map) return;
		const drawable = (regions?.features ?? []).filter((f) => f.geometry);
		(map.getSource('regions') as GeoJSONSource).setData({ type: 'FeatureCollection', features: drawable } as FeatureCollection);
		const hover: ExpressionSpecification = ['boolean', ['feature-state', 'hover'], false];
		map.setPaintProperty('regions-fill', 'fill-opacity', onregion ? ['case', hover, 0.45, 0.22] : 0.05);
		map.setPaintProperty('regions-line', 'line-width', onregion ? ['case', hover, 2.5, 1.5] : 2);
		map.setPaintProperty('regions-line', 'line-dasharray', onregion ? [1, 0] : [3, 2]);
	});

	// Data and layer visibility
	$effect(() => {
		if (!ready || !map) return;
		(map.getSource('apps') as GeoJSONSource).setData(appellations ? shadeAppellations(appellations) : EMPTY);
		(map.getSource('vines') as GeoJSONSource).setData(vineyards ? shadeVineyards(vineyards) : EMPTY);
		if (fitKey !== fitted && (extent || appellations || vineyards)) {
			const b = extent ?? bbox([...(appellations?.features ?? []), ...(vineyards?.features ?? [])].map((f) => f.geometry));
			if (b) {
				fitted = fitKey;
				map.fitBounds(b, { padding: 40, duration: 0 });
			}
		}
	});

	$effect(() => {
		if (!ready || !map) return;
		for (const id of ['apps-fill', 'apps-line']) map.setLayoutProperty(id, 'visibility', showAppellations ? 'visible' : 'none');
		for (const id of ['vines-fill', 'vines-line']) map.setLayoutProperty(id, 'visibility', showVineyards ? 'visible' : 'none');
	});

	// Selection outline follows the theme's accent
	$effect(() => {
		if (!ready || !map) return;
		const sel: ExpressionSpecification = ['boolean', ['feature-state', 'selected'], false];
		map.setPaintProperty('apps-line', 'line-color', ['case', sel, accentColor(), ['coalesce', ['get', 'color'], FALLBACK_REGION]]);
		map.setPaintProperty('vines-line', 'line-color', ['case', sel, accentColor(), ['get', 'edge']]);
	});

	// Selection highlight
	let selRef: { source: string; id: number } | null = null;
	$effect(() => {
		if (!ready || !map) return;
		void appellations, vineyards; // re-apply after setData clears feature state
		if (selRef) map.setFeatureState(selRef, { selected: false });
		selRef = selected ? { source: selected.kind === 'appellation' ? 'apps' : 'vines', id: selected.id } : null;
		if (selRef) map.setFeatureState(selRef, { selected: true });
	});

	$effect(() => {
		if (!ready || !map) return;
		setBasemap(map, basemap, theme.dark);
	});
</script>

<div class="wrap">
	<div class="canvas" bind:this={container}></div>
	{#if hoveredRegion}
		<div class="hover card">
			<div class="kind">region{hoveredRegion.country && hoveredRegion.country !== hoveredRegion.name ? ` · ${hoveredRegion.country}` : ''}</div>
			<b>{hoveredRegion.name}</b>
			<div class="muted num">
				{[hoveredRegion.appellations && plural(hoveredRegion.appellations, 'appellation'), hoveredRegion.vineyards && plural(hoveredRegion.vineyards, 'vineyard')].filter(Boolean).join(' · ')}
			</div>
			{#if hoveredRegion.bottles}<div class="num owned">{hoveredRegion.bottles} btl in cellar · {money(hoveredRegion.value)}</div>{/if}
			{#if hoveredRegion.tastings}<div class="num tasted">✎ {plural(hoveredRegion.tastings, 'tasting')}</div>{/if}
			<div class="muted hint">Click to explore</div>
		</div>
	{:else if card}
		<div class="hover card" class:pinned={isPinned}>
			{#if isPinned}<button class="close" onclick={() => onselect(null)} aria-label="Close">✕</button>{/if}
			<div class="kind">{card.kind}</div>
			<b>{card.name}</b>
			{#if card.village || card.subregion}
				<div class="muted">{[card.subregion, card.village].filter(Boolean).join(' · ')}</div>
			{/if}
			{#if card.bottles}<div class="num owned">{card.bottles} btl in cellar · {money(card.value)}</div>{/if}
			{#if card.tastings}
				<div class="num tasted">✎ {plural(card.tastings, 'tasting')}</div>
			{/if}
			{#if isPinned}
				<a class="go" href={detailsUrl(card)}>Details →</a>
			{:else if pinCard}
				<div class="muted hint">Click for details</div>
			{/if}
		</div>
	{/if}
</div>

<style>
	.wrap {
		position: absolute;
		inset: 0;
	}
	.canvas {
		position: absolute;
		inset: 0;
	}
	.hover {
		position: absolute;
		left: 12px;
		top: 12px;
		padding: 9px 12px;
		pointer-events: none;
		font-size: 13px;
		max-width: 300px;
	}
	.hover.pinned {
		pointer-events: auto;
		padding-right: 30px;
	}
	.close {
		position: absolute;
		top: 6px;
		right: 6px;
		border: none;
		background: none;
		color: var(--muted);
		cursor: pointer;
		font-size: 12px;
	}
	.tasted {
		color: var(--accent);
		font-weight: 600;
	}
	.go {
		display: inline-block;
		margin-top: 4px;
		font-weight: 600;
	}
	.hint {
		font-size: 11px;
		margin-top: 2px;
	}
	.kind {
		font-size: 10px;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--muted);
	}
	.owned {
		color: var(--gold);
		font-weight: 600;
	}
</style>

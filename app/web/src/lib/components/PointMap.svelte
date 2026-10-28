<script lang="ts" module>
	export interface MapPoint {
		id: number;
		lat: number;
		lng: number;
		label: string;
		/** second line in the hover card */
		sub?: string;
		color?: string;
		/** drives the circle size, e.g. number of tastings */
		weight?: number;
	}
</script>

<script lang="ts">
	import { onMount } from 'svelte';
	import 'maplibre-gl/dist/maplibre-gl.css';
	import type { GeoJSONSource, Map as MlMap } from 'maplibre-gl';
	import { createMap, setBasemap } from '#lib/basemap.ts';
	import { accentColor, theme } from '#lib/theme.svelte.ts';
	import type { Basemap } from '#lib/basemap.ts';

	interface Props {
		points: MapPoint[];
		selectedId?: number | null;
		onselect?: (id: number | null) => void;
		basemap?: Basemap;
		/** zoom used when there is a single point */
		zoom?: number;
	}

	let { points, selectedId = null, onselect, basemap = 'plain', zoom = 14 }: Props = $props();

	let container: HTMLDivElement;
	let map = $state<MlMap>();
	let hovered = $state<MapPoint | null>(null);
	let fittedFor = '';

	const collection = $derived({
		type: 'FeatureCollection' as const,
		features: points.map((p) => ({
			type: 'Feature' as const,
			id: p.id,
			geometry: { type: 'Point' as const, coordinates: [p.lng, p.lat] },
			properties: { id: p.id, color: p.color ?? accentColor(), weight: p.weight ?? 1 }
		}))
	});
	const maxWeight = $derived(Math.max(1, ...points.map((p) => p.weight ?? 1)));

	onMount(() => {
		let m: MlMap | undefined;
		// left before the map was ready (a quick click on): the map made afterwards is removed at once, not leaked
		let gone = false;
		(async () => {
			m = await createMap(container, basemap);
			if (gone) return m.remove();
			m.addSource('points', { type: 'geojson', data: { type: 'FeatureCollection', features: [] }, promoteId: 'id' });
			m.addLayer({
				id: 'points', type: 'circle', source: 'points',
				paint: {
					'circle-color': ['get', 'color'],
					'circle-opacity': 0.8,
					'circle-radius': ['interpolate', ['linear'], ['sqrt', ['get', 'weight']], 1, 6, Math.sqrt(1000), 22],
					'circle-stroke-color': ['case', ['boolean', ['feature-state', 'selected'], false], '#d4af37', '#ffffff'],
					'circle-stroke-width': ['case', ['boolean', ['feature-state', 'selected'], false], 3, 1.5]
				}
			});
			m.on('mousemove', 'points', (e) => {
				const id = e.features?.[0]?.id as number | undefined;
				hovered = points.find((p) => p.id === id) ?? null;
				m!.getCanvas().style.cursor = 'pointer';
			});
			m.on('mouseleave', 'points', () => {
				hovered = null;
				m!.getCanvas().style.cursor = '';
			});
			m.on('click', (e) => {
				const f = m!.queryRenderedFeatures(e.point, { layers: ['points'] })[0];
				onselect?.(f ? (f.id as number) : null);
			});
			map = m;
		})();
		return () => {
			gone = true;
			m?.remove();
		};
	});

	$effect(() => {
		if (!map) return;
		(map.getSource('points') as GeoJSONSource).setData(collection);
		// Refit when the set of points changes, not on every re-render
		const key = points.map((p) => p.id).join(',');
		if (key === fittedFor || !points.length) return;
		fittedFor = key;
		if (points.length === 1) map.jumpTo({ center: [points[0].lng, points[0].lat], zoom });
		else {
			const lngs = points.map((p) => p.lng), lats = points.map((p) => p.lat);
			map.fitBounds([Math.min(...lngs), Math.min(...lats), Math.max(...lngs), Math.max(...lats)], { padding: 50, maxZoom: zoom, duration: 0 });
		}
	});

	let selectedRef: number | null = null;
	$effect(() => {
		if (!map) return;
		void collection;
		if (selectedRef !== null) map.setFeatureState({ source: 'points', id: selectedRef }, { selected: false });
		selectedRef = selectedId;
		if (selectedId !== null) map.setFeatureState({ source: 'points', id: selectedId }, { selected: true });
	});

	$effect(() => {
		if (!map) return;
		setBasemap(map, basemap, theme.dark);
	});

	// keep the weight scale in step with the data (stops must ascend strictly, even when every weight is 1)
	$effect(() => {
		if (!map) return;
		map.setPaintProperty('points', 'circle-radius', ['interpolate', ['linear'], ['sqrt', ['get', 'weight']], 1, 6, Math.max(Math.sqrt(maxWeight), 2), 22]);
	});
</script>

<div class="wrap">
	<div class="canvas" bind:this={container}></div>
	{#if hovered}
		<div class="hover card">
			<b>{hovered.label}</b>
			{#if hovered.sub}<div class="muted">{hovered.sub}</div>{/if}
		</div>
	{/if}
</div>

<style>
	.wrap,
	.canvas {
		position: absolute;
		inset: 0;
	}
	.hover {
		position: absolute;
		left: 12px;
		top: 12px;
		padding: 8px 12px;
		pointer-events: none;
		font-size: 13px;
		max-width: 280px;
	}
</style>

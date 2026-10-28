<script lang="ts" module>
	export type { Basemap } from '#lib/basemap.ts';
	export type Selection = { kind: 'appellation' | 'vineyard'; id: number } | null;
	/** What a lieu-dit's card offers (a wine page: "Make it this wine's vineyard"): its label, and what it does with
	 * the lieu-dit's store id ("lieu_dit:49060:les-poyeux") */
	export type LieuAction = { label: string; run: (id: string) => Promise<unknown> };
	/** How a kind of shape is drawn (LayerToggle cycles them): filled, its outline only, or not at all */
	export type LayerMode = 'fill' | 'outline' | 'off';
	export interface Layers {
		appellation: LayerMode;
		vineyard: LayerMode;
		/** the cadastre's lieux-dits, from close zoom */
		lieu: LayerMode;
	}
	export const DEFAULT_LAYERS: Layers = { appellation: 'fill', vineyard: 'fill', lieu: 'outline' };
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
	import { cruShade, darken } from '#lib/cru.ts';
	import { accentColor, theme } from '#lib/theme.svelte.ts';
	import type { Basemap } from '#lib/basemap.ts';

	interface Props {
		appellations: MapCollection | null;
		vineyards: MapCollection | null;
		/** how each kind is drawn (filled, outlined, hidden) */
		layers?: Layers;
		/** the page's own shape: its card has no link to its page */
		here?: Selection;
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
		/** clicking a region opens its card with a link to this page (the home map), instead of onregion */
		regionHref?: ((r: RegionProps) => string) | null;
		/** what a lieu-dit's card offers when clicked */
		lieuAction?: LieuAction | null;
		/** where the hover card sits: the right when something covers the map's left (a full map's page column) */
		cardSide?: 'left' | 'right';
		/** pixels on the left covered by something (a full map's page column): framed in the rest */
		padLeft?: number;
		/** pixels at the bottom covered by something (a phone's page sheet over a full map) */
		padBottom?: number;
		/** the map once ready (a drawing toolbar works on it) */
		onmap?: (m: MlMap) => void;
		/** no cards nor clicks of its own (while an outline is drawn on it) */
		quiet?: boolean;
		/** the world repeated side by side when zoomed out (off: a wide box shows one world) */
		worldCopies?: boolean;
	}

	let {
		appellations, vineyards, layers = DEFAULT_LAYERS, here = null,
		selected, basemap, fitKey, extent = null, onselect, pinCard = true,
		regions = null, onregion = null, regionHref = null, worldCopies = true, lieuAction = null, cardSide = 'left', padLeft = 0, padBottom = 0,
		onmap, quiet = false
	}: Props = $props();

	/** Vineyards in their region's tones, as the appellations: a notch darker (a cru darker still), their outline
	 * darker again, so they read as the finer grain inside an appellation */
	function shadeVineyards(fc: MapCollection): MapCollection {
		return {
			...fc,
			features: fc.features.map((f) => {
				const color = f.properties.color ?? FALLBACK_REGION;
				const cru = f.properties.cru ?? 0;
				return { ...f, properties: { ...f.properties, fill: darken(color, cru + 1), edge: darken(color, cru + 2) } };
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
	// The cadastre's lieux-dits in view (zoomed in, with the vineyards shown): read from the store as the map moves
	type LieuProps = { id: string; name: string; village: string | null; aocs: string | null; vines: number | null; vineyard_id?: number | null };
	let lieuBusy = $state(false);
	let lieuError = $state('');
	async function runLieu(l: LieuProps) {
		if (!lieuAction) return;
		lieuBusy = true;
		lieuError = '';
		try {
			await lieuAction.run(l.id);
			pinnedLieu = null;
		} catch (e) {
			lieuError = e instanceof Error ? e.message : 'Couldn’t do it';
		} finally {
			lieuBusy = false;
		}
	}
	let hoveredLieu = $state<LieuProps | null>(null);
	let pinnedLieu = $state<LieuProps | null>(null);
	// a clicked lieu-dit's card stays (its buttons within reach) while the pointer crosses others on the way to it
	const lieu = $derived(pinnedLieu ?? hoveredLieu);
	const framing = () => ({ top: 40, right: 40, bottom: 40 + padBottom, left: 40 + padLeft });
	// the clicked one (its card keeps its buttons while the pointer is still over it)
	const lieuPinned = $derived(!!lieu && !!pinnedLieu && lieu.id === pinnedLieu.id);
	const LIEUX_ZOOM = 12;
	// asks for the lieux-dits in view again (set once the map is ready)
	let reloadLieux: (() => void) | null = null;
	let hoveredRegion = $state<RegionProps | null>(null);
	// a region clicked (regionHref): its card stays, with its link
	let pinnedRegion = $state<RegionProps | null>(null);
	const regionCard = $derived(hoveredRegion ?? pinnedRegion);
	const regionPinned = $derived(!!pinnedRegion && regionCard === pinnedRegion);
	const regionsAnswer = $derived(!!(onregion || regionHref));
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
			// Opened where it will be fitted, when that's already known (the home page's map)
			m = await createMap(container, basemap, extent ? { bounds: extent, fitBoundsOptions: { padding: framing() } } : undefined);
			if (!worldCopies) m.setRenderWorldCopies(false);
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
				// Lieux-dits: a fine dashed line, filled only under the pointer (under the vineyards, over the appellations)
				mm.addSource('lieux', { type: 'geojson', data: EMPTY, generateId: true });
				mm.addLayer({
					id: 'lieux-fill', type: 'fill', source: 'lieux', minzoom: LIEUX_ZOOM,
					paint: { 'fill-color': '#f2e6c9', 'fill-opacity': ['case', hover, 0.25, 0.01] }
				});
				mm.addLayer({
					id: 'lieux-line', type: 'line', source: 'lieux', minzoom: LIEUX_ZOOM,
					paint: { 'line-color': '#f2e6c9', 'line-opacity': 0.75, 'line-width': ['case', hover, 1.6, 0.7], 'line-dasharray': [3, 2] }
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
						layers: regionsAnswer ? ['vines-fill', 'lieux-fill', 'apps-fill', 'regions-fill'] : ['vines-fill', 'lieux-fill', 'apps-fill']
					})[0];
				// Rendered features carry flattened properties: take the region's own
				const regionOf = (id: unknown) => regions?.features.find((r) => r.properties.id === id)?.properties ?? null;

				mm.on('mousemove', (e) => {
					if (quiet) return;
					const f = topFeature(e.point);
					setHover(f ? { source: f.source, id: f.id as number } : null);
					const isRegion = f?.source === 'regions';
					const isLieu = f?.source === 'lieux';
					hoveredLieu = isLieu ? (f.properties as LieuProps) : null;
					hovered = f && !isRegion && !isLieu ? (f.properties as MapProps) : null;
					hoveredRegion = isRegion ? regionOf(f.id) : null;
					mm.getCanvas().style.cursor = f ? 'pointer' : '';
				});
				mm.on('mouseout', () => {
					setHover(null);
					hovered = null;
					hoveredRegion = null;
					hoveredLieu = null;
				});
				mm.on('click', (e) => {
					if (quiet) return;
					const f = topFeature(e.point);
					pinnedLieu = f?.source === 'lieux' ? (f.properties as LieuProps) : null;
					pinnedRegion = f?.source === 'regions' && regionHref ? regionOf(f.id) : null;
					if (f?.source === 'lieux') return;
					if (f?.source === 'regions') {
						const r = regionOf(f.id);
						if (r && onregion && !regionHref) onregion(r);
					} else onselect(f ? (f.properties as MapProps) : null);
				});
				// The lieux-dits in view, asked again a moment after the map stops moving
				let lieuxTimer: ReturnType<typeof setTimeout>;
				let lieuxAsked = '';
				const loadLieux = () => {
					clearTimeout(lieuxTimer);
					lieuxTimer = setTimeout(async () => {
						const source = mm.getSource('lieux') as GeoJSONSource | undefined;
						if (!source || mm.getZoom() < LIEUX_ZOOM || (layers.lieu === 'off' && !quiet)) return;
						const b = mm.getBounds();
						const bbox = [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()].map((x) => x.toFixed(3)).join(',');
						if (bbox === lieuxAsked) return;
						lieuxAsked = bbox;
						const r = await fetch(`/api/map/lieux-dits?bbox=${bbox}`).then((x) => (x.ok ? x.json() : null)).catch(() => null);
						if (r && bbox === lieuxAsked) source.setData(r);
					}, 250);
				};
				mm.on('moveend', loadLieux);
				const sized = new ResizeObserver(() => mm.resize());
				sized.observe(container);
				mm.once('remove', () => sized.disconnect());
				loadLieux();
				map = mm;
				// Their names, while an outline is drawn (quiet: no cards to tell them), over everything
				mm.addLayer({
					id: 'lieux-label', type: 'symbol', source: 'lieux', minzoom: 13,
					layout: { 'text-field': ['get', 'name'], 'text-font': ['Noto Sans Regular'], 'text-size': 11, 'text-max-width': 8, visibility: 'none' },
					paint: { 'text-color': '#ffffff', 'text-halo-color': '#1c1a1f', 'text-halo-width': 1.4 }
				});
				reloadLieux = loadLieux;
				ready = true;
				onmap?.(mm);
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
		map.setPaintProperty('regions-fill', 'fill-opacity', regionsAnswer ? ['case', hover, 0.45, 0.22] : 0.05);
		map.setPaintProperty('regions-line', 'line-width', regionsAnswer ? ['case', hover, 2.5, 1.5] : 2);
		map.setPaintProperty('regions-line', 'line-dasharray', regionsAnswer ? [1, 0] : [3, 2]);
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
				map.fitBounds(b, { padding: framing(), duration: 0 });
			}
		}
	});

	$effect(() => {
		if (!ready || !map) return;
		const on = (m: LayerMode) => (m === 'off' ? 'none' : 'visible');
		for (const id of ['apps-fill', 'apps-line']) map.setLayoutProperty(id, 'visibility', on(layers.appellation));
		for (const id of ['vines-fill', 'vines-line']) map.setLayoutProperty(id, 'visibility', on(layers.vineyard));
		// the lieux-dits always while drawing (their outlines and names to draw along)
		for (const id of ['lieux-fill', 'lieux-line']) map.setLayoutProperty(id, 'visibility', layers.lieu !== 'off' || quiet ? 'visible' : 'none');
		map.setLayoutProperty('lieux-label', 'visibility', quiet ? 'visible' : 'none');
		if (layers.lieu !== 'off' || quiet) reloadLieux?.();
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
		if (selected) {
			pinnedLieu = null;
			pinnedRegion = null;
		}
		if (selRef) map.setFeatureState(selRef, { selected: false });
		selRef = selected ? { source: selected.kind === 'appellation' ? 'apps' : 'vines', id: selected.id } : null;
		if (selRef) map.setFeatureState(selRef, { selected: true });
	});

	$effect(() => {
		if (!quiet) return;
		hovered = null;
		hoveredRegion = null;
		hoveredLieu = null;
		pinnedLieu = null;
	});

	$effect(() => {
		if (!ready || !map) return;
		setBasemap(map, basemap, theme.dark);
		// on the photos, the fills light enough to see the vines under them (the outlines carry the shapes)
		const photo = basemap === 'satellite';
		const hover: ExpressionSpecification = ['boolean', ['feature-state', 'hover'], false];
		const sel: ExpressionSpecification = ['boolean', ['feature-state', 'selected'], false];
		// zoomed in to the lieux-dits (LIEUX_ZOOM on), the fills fade so their outlines read through: an appellation
		// almost to its outline, a vineyard to a tint
		// an outline only: no fill but a touch under the pointer or selected (what's there, what's picked)
		const vines = (k: number): ExpressionSpecification => layers.vineyard === 'outline'
			? ['case', sel, 0.18, hover, 0.12, 0]
			: ['case', sel, (photo ? 0.4 : 0.95) * k, hover, (photo ? 0.35 : 0.92) * k, (photo ? 0.22 : 0.8) * k];
		const apps = (k: number): ExpressionSpecification => layers.appellation === 'outline'
			? ['case', sel, 0.12, hover, 0.08, 0]
			: ['case', sel, (photo ? 0.18 : 0.4) * k, hover, (photo ? 0.14 : 0.3) * k, ['boolean', ['get', 'umbrella'], false], 0, (photo ? 0.06 : 0.16) * k];
		map.setPaintProperty('vines-fill', 'fill-opacity', ['interpolate', ['linear'], ['zoom'], LIEUX_ZOOM - 1, vines(1), LIEUX_ZOOM + 1, vines(0.55)]);
		map.setPaintProperty('apps-fill', 'fill-opacity', ['interpolate', ['linear'], ['zoom'], LIEUX_ZOOM - 1, apps(1), LIEUX_ZOOM + 1, apps(0.25)]);
		// the lieux-dits' dashes: cream over a dark or photo basemap, a warm grey over the light Plain one
		const lieu = basemap === 'plain' && !theme.dark ? '#8f8389' : '#f2e6c9';
		if (map.getLayer('lieux-line')) {
			map.setPaintProperty('lieux-line', 'line-color', lieu);
			map.setPaintProperty('lieux-fill', 'fill-color', lieu);
			map.setPaintProperty('lieux-fill', 'fill-opacity', layers.lieu === 'fill' ? ['case', hover, 0.4, 0.2] : ['case', hover, 0.25, 0.01]);
			const light = basemap === 'plain' && !theme.dark;
			map.setPaintProperty('lieux-label', 'text-color', light ? '#4a4448' : '#ffffff');
			map.setPaintProperty('lieux-label', 'text-halo-color', light ? '#f3f0eb' : '#1c1a1f');
		}
	});
</script>

<div class="wrap">
	<div class="canvas" bind:this={container}></div>
	{#if regionCard}
		<div class="hover card" class:right={cardSide === 'right'} class:low={padBottom > 0} style:bottom={padBottom > 0 ? `${padBottom + 36}px` : null} class:pinned={regionPinned}>
			{#if regionPinned}<button class="close" onclick={() => (pinnedRegion = null)} aria-label="Close">✕</button>{/if}
			<div class="kind">region{regionCard.country && regionCard.country !== regionCard.name ? ` · ${regionCard.country}` : ''}</div>
			<b>{regionCard.name}</b>
			<div class="muted num">
				{[regionCard.appellations && plural(regionCard.appellations, 'appellation'), regionCard.vineyards && plural(regionCard.vineyards, 'vineyard')].filter(Boolean).join(' · ')}
			</div>
			{#if regionCard.bottles}<div class="num owned">{regionCard.bottles} btl in cellar · {money(regionCard.value)}</div>{/if}
			{#if regionCard.tastings}<div class="num tasted">✎ {plural(regionCard.tastings, 'tasting')}</div>{/if}
			{#if regionPinned && regionHref}<a class="go" href={regionHref(regionCard)}>Open region →</a>
			{:else}<div class="muted hint">{regionHref ? 'Click for more' : 'Click to explore'}</div>{/if}
		</div>
	{:else if lieu}
		<div class="hover card" class:right={cardSide === 'right'} class:low={padBottom > 0} style:bottom={padBottom > 0 ? `${padBottom + 36}px` : null} class:pinned={lieuPinned}>
			{#if lieuPinned}<button class="close" onclick={() => (pinnedLieu = null)} aria-label="Close">✕</button>{/if}
			<div class="kind">lieu-dit · cadastre</div>
			<b>{lieu.name}</b>
			{#if lieu.village}<div class="muted">{lieu.village}</div>{/if}
			{#if lieu.aocs}<div class="aocs">{lieu.aocs.split('; ').slice(0, 3).join(' · ')}{lieu.aocs.split('; ').length > 3 ? ' …' : ''}</div>{/if}
			{#if lieu.vines}<div class="muted num">{Math.round(lieu.vines * 100)}% in AOC vines</div>{/if}
			{#if lieuPinned}
				{#if lieu.vineyard_id}<a class="go" href={links.vineyard(lieu.vineyard_id)}>Its page →</a>{/if}
				{#if lieuAction}
					<button class="lieu-action" disabled={lieuBusy} onclick={() => runLieu(lieu!)}>{lieuBusy ? 'Saving…' : lieuAction.label}</button>
					{#if lieuError}<div class="lieu-error">{lieuError}</div>{/if}
				{/if}
			{:else if lieuAction || lieu.vineyard_id}
				<div class="muted hint">Click for more</div>
			{/if}
		</div>
	{:else if card}
		<div class="hover card" class:right={cardSide === 'right'} class:low={padBottom > 0} style:bottom={padBottom > 0 ? `${padBottom + 36}px` : null} class:pinned={isPinned}>
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
			{#if isPinned && !(here && here.kind === card.kind && here.id === card.id)}
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
	.hover.right {
		left: auto;
		right: 56px;
	}
	/* the map's bottom covered (a phone's page sheet), its top the controls: the card just above what covers it */
	.hover.low {
		top: auto;
		left: 12px;
		right: 12px;
		max-width: none;
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
	.lieu-action {
		margin-top: 8px;
		padding: 5px 10px;
		border: none;
		border-radius: 7px;
		background: var(--accent);
		color: #fff;
		font: inherit;
		font-size: 12px;
		cursor: pointer;
	}
	.lieu-error {
		color: var(--down);
		font-size: 12px;
		margin-top: 4px;
	}
	.aocs {
		font-size: 12px;
		margin-top: 2px;
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

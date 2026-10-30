<script lang="ts">
	import WineMap from '#lib/components/WineMap.svelte';
	import type { Basemap, Selection } from '#lib/components/WineMap.svelte';
	import type { Shapes } from '#lib/api/details.ts';
	import { bbox } from '#lib/geo.ts';
	import { links } from '#lib/links.ts';
	import type { MapCollection, MapProps } from '#lib/types.ts';
	import { appSettings } from '#lib/settings.svelte.ts';
	import { cruShade, darken } from '#lib/cru.ts';
	import { FALLBACK_REGION } from '#lib/colors.ts';
	import { untrack } from 'svelte';
	import { portal } from '#lib/portal.ts';
	import { mapView } from '#lib/mapView.svelte.ts';
	import type { LieuAction, Layers } from '#lib/components/WineMap.svelte';
	import { DEFAULT_LAYERS } from '#lib/components/WineMap.svelte';
	import LayerToggle from '#lib/components/LayerToggle.svelte';
	import type { Map as MlMap } from 'maplibre-gl';
	import OutlineTools from './OutlineTools.svelte';
	import type { DrawSpec } from './OutlineTools.svelte';

	interface Props {
		/** a shapes endpoint (see shapesUrl) */
		src: string;
		/** the page's own appellation / vineyard: the map frames it (no outline, so it reads like its neighbours) */
		current?: Selection;
		/** what the map opens on when it isn't the page's own shape (a wine's vineyard, among its appellation) */
		frame?: Selection;
		height?: number;
		/** shown when there is nothing to draw */
		empty?: string;
		/** the page's own shape at full detail (/outline/full), when the shape store has it: a "Full detail" toggle */
		fullUrl?: string | null;
		/** what a lieu-dit's card offers (a wine page: make it the wine's vineyard) */
		lieuAction?: LieuAction | null;
		/** an outline to draw on this map (Draw outline, Draw vineyard): it goes full size, its view kept */
		draw?: DrawSpec | null;
		/** the drawing closed: saved (or the new vineyard's id) */
		ondrawn?: (saved: boolean, created?: number) => void;
		/** the page's own tastings and bottles by shape ("appellation:12", "vineyard:3"): badges in the legend (the
		 * shapes' own figures are the whole cellar's) */
		counts?: Record<string, { bottles: number; tastings: number }> | null;
		/** bound: loaded with nothing to draw (no boundary data): its "no data" line in place of the map */
		nothing?: boolean;
	}

	let { src, current = null, frame = null, height = 320, empty = 'No boundary data for this one.', fullUrl = null, lieuAction = null, draw = null, ondrawn, counts = null, nothing = $bindable(false) }: Props = $props();

	// Full size (Settings › Appearance, or ⤢ here): the map fills the window behind the page, which becomes a column
	// of cards over its left side (html.map-full in app.css); Esc goes back. Not for a map with nothing to show (no
	// boundary data): the page stays as it is, its "no data" line in place of the map
	const big = $derived.by(() => mapView.full && !blank);
	$effect(() => {
		document.documentElement.classList.toggle('map-full', big);
		return () => document.documentElement.classList.remove('map-full');
	});
	// Each page opens as Settings › Appearance says (full size or in the page); the same page reloading its map (a
	// vineyard just linked from it) stays as it is
	const page = $derived(src.split('?')[0]);
	$effect(() => {
		page;
		mapView.full = untrack(() => mapView.always);
	});
	function onkey(e: KeyboardEvent) {
		if (big && !drawing && e.key === 'Escape') mapView.full = false;
	}

	// Drawing an outline (draw): on this very map, full size (as it was when done), on the photos (put back after)
	let mlmap = $state<MlMap | null>(null);
	// the window's size, followed (a phone turned, a window resized): what the page's column or sheet covers
	let winWidth = $state(1024);
	let winHeight = $state(768);
	let drawing = $state<DrawSpec | null>(null);
	let before: { full: boolean; basemap: Basemap } | null = null;
	$effect(() => {
		if (!draw || drawing) return;
		untrack(() => {
			before = { full: mapView.full, basemap };
			mapView.full = true;
			basemap = 'satellite';
			drawing = draw;
		});
	});
	$effect(() => {
		document.documentElement.classList.toggle('map-drawing', !!drawing);
		return () => document.documentElement.classList.remove('map-drawing');
	});
	function drawn(saved: boolean, created?: number) {
		drawing = null;
		if (before) ({ full: mapView.full, basemap } = before);
		before = null;
		ondrawn?.(saved, created);
	}

	let shapes = $state<Shapes | null>(null);
	let failed = $state(false);
	// nothing to draw: the map failed, or came back empty (and isn't being drawn on)
	const blank = $derived.by(() => failed || (!!shapes && !count && !outline && !drawing));
	let basemap = $state<Basemap>(appSettings.map_default_basemap);

	$effect(() => {
		let cancelled = false;
		shapes = null;
		failed = false;
		fetch(src)
			.then((r) => (r.ok ? r.json() : Promise.reject()))
			.then((d: Shapes) => !cancelled && (shapes = d))
			.catch(() => !cancelled && (failed = true));
		return () => (cancelled = true);
	});

	// Full detail: the page's own shape swapped for its full outline, fetched on the first click
	let full = $state(false);
	let fullGeometry = $state<import('geojson').Geometry | null>(null);
	let fullLoading = $state(false);
	$effect(() => {
		fullUrl;
		full = false;
		fullGeometry = null;
	});
	async function toggleFull() {
		full = !full;
		if (!full || fullGeometry || !fullUrl) return;
		fullLoading = true;
		try {
			const r = await fetch(fullUrl);
			if (!r.ok) throw new Error();
			fullGeometry = (await r.json()).geometry;
		} catch {
			full = false;
		} finally {
			fullLoading = false;
		}
	}
	// The collections the map draws: the current shape's geometry replaced while Full detail is on
	const swap = (fc: MapCollection, kind: string) =>
		full && fullGeometry && current?.kind === kind
			? { ...fc, features: fc.features.map((f) => (f.properties.id === current.id ? { ...f, geometry: fullGeometry! } : f)) }
			: fc;
	// The legend's entries hidden one by one (their swatch): left out of what the map draws
	let hidden = $state<Set<string>>(new Set());
	const keyOf = (k: { kind: string; id: number | string }) => `${k.kind}:${k.id}`;
	const shown = (fc: MapCollection) =>
		hidden.size ? { ...fc, features: fc.features.filter((f) => !hidden.has(keyOf(f.properties))) } : fc;
	function toggleShown(k: MapProps) {
		const next = new Set(hidden);
		if (!next.delete(keyOf(k))) {
			next.add(keyOf(k));
			if (focused(k)) focus = null; // a hidden shape isn't zoomed to
		}
		hidden = next;
	}
	const drawnApps = $derived(shapes ? shown(swap(shapes.appellations, 'appellation')) : null);
	const drawnVines = $derived(shapes ? shown(swap(shapes.vineyards, 'vineyard')) : null);

	const outline = $derived(shapes?.region?.features.length ? { ...shapes.region, extent: null } : null);
	$effect(() => {
		nothing = blank;
	});
	const count = $derived((shapes?.appellations.features.length ?? 0) + (shapes?.vineyards.features.length ?? 0));
	const keys = $derived(shapes ? [...shapes.appellations.features, ...shapes.vineyards.features].map((f) => f.properties) : []);
	const missing = $derived(shapes ? [...shapes.appellations.missing, ...shapes.vineyards.missing] : []);

	// The legend's zoomed-to shape (a second click on it frames everything again), and the shape clicked on the map:
	// either shows its card (name, details, a link to its page); nothing here leaves the page
	let focus = $state<Selection>(null);
	let picked = $state<Selection>(null);
	let focusCard = $state(false);
	const selected = $derived(picked ?? (focusCard ? focus : null));
	$effect(() => {
		src;
		focus = null;
		picked = null;
		hidden = new Set();
	});
	function pick(p: MapProps | null) {
		picked = p ? { kind: p.kind, id: p.id } : null;
		if (!p) focusCard = false;
	}
	function zoomTo(k: MapProps) {
		if (layers[k.kind] === 'off') layers[k.kind] = 'fill';
		if (hidden.has(keyOf(k))) toggleShown(k); // zooming to it shows it again
		picked = null;
		focus = focused(k) ? null : { kind: k.kind, id: k.id };
		focusCard = !!focus;
	}

	// Frame the page's own shape (or the focused one); its neighbours show around it
	const extent = $derived.by(() => {
		if (outline && !focus) return outline.features[0].properties.bbox; // a region page frames the whole region
		const target = focus ?? current ?? frame;
		if (!shapes || !target) return null;
		const fc = target.kind === 'appellation' ? shapes.appellations : shapes.vineyards;
		const f = fc.features.find((f) => f.properties.id === target.id);
		const b = f ? bbox([f.geometry]) : null;
		if (!b || target.kind !== 'vineyard') return b;
		// a vineyard at the vineyards' scale, not filling the map: at least ~1.5 km across, its neighbours around it
		const [w, s, e, n] = b;
		const dx = Math.max(e - w, 0.02) * 0.75, dy = Math.max(n - s, 0.012) * 0.75;
		const x = (w + e) / 2, y = (s + n) / 2;
		return [x - dx, y - dy, x + dx, y + dy] as typeof b;
	});
	const fitKey = $derived(focus ? `${src}#${focus.kind}:${focus.id}` : src);
	const focused = (k: MapProps) => focus?.kind === k.kind && focus.id === k.id;

	// Each kind filled, outlined or hidden (LayerToggle)
	let layers = $state<Layers>({ ...DEFAULT_LAYERS });
	const appColor = $derived(shapes?.appellations.features[0]?.properties.color ?? FALLBACK_REGION);
</script>

<svelte:window onkeydown={onkey} bind:innerWidth={winWidth} bind:innerHeight={winHeight} />

{#if blank}
	<div class="empty muted" style:min-height="{Math.min(height, 120)}px">
		{#if failed}The map couldn’t load.
		{:else if shapes?.outlines === false}No map outlines installed yet: <a href={links.settings('maintenance')}>Settings › Maintenance › Map outlines</a> downloads them.
		{:else}{empty}{/if}
	</div>
{:else}
	<!-- the same element in the page or full size (moved, not redrawn): the map keeps its view -->
	<div class="fullmap" class:on={big} use:portal={big} role="region" aria-label={big ? 'The map, full size' : 'The map'}>
		{@render figure()}
		{#if drawing && mlmap && big}<OutlineTools map={mlmap} spec={drawing} bind:basemap frame={!count} onclose={drawn} />{/if}
	</div>
{/if}

{#snippet figure()}
	<figure class:big>
		<div class="map" style:height={big ? null : `${height}px`}>
			{#if shapes}
				<WineMap
					appellations={drawnApps}
					vineyards={drawnVines}
					{selected}
					{layers}
					here={current}
					{basemap}
					{fitKey}
					{extent}
					onselect={pick}
					regions={outline}
					{lieuAction}
					cardSide={big ? 'right' : 'left'}
					padLeft={big && winWidth > 760 ? 560 : 0}
					padBottom={big && winWidth <= 760 && !drawing ? Math.round(winHeight * 0.45) : 0}
					onmap={(m) => (mlmap = m)}
					quiet={!!drawing}
				/>
			{:else}
				<div class="loading muted">Loading map…</div>
			{/if}
		</div>
		{#if shapes && !drawing}
			<figcaption>
				<!-- one row: the layers at the left, the map's buttons at the right -->
				<div class="bar">
				<div class="kinds">
					<LayerToggle label="Appellations" bind:mode={layers.appellation} swatch={appColor} />
					<LayerToggle label="Vineyards" bind:mode={layers.vineyard} swatch={darken(appColor, 1)} />
					<LayerToggle label="Lieux-dits" bind:mode={layers.lieu} dashed />
				</div>
				<div class="seg">
					{#each [['plain', 'Plain'], ['satellite', 'Satellite']] as [id, label]}
						<button class:on={basemap === id} aria-pressed={basemap === id} onclick={() => (basemap = id as Basemap)}>{label}</button>
					{/each}
				</div>
				{#if fullUrl}
					<div class="seg detail">
						<button class:on={full} aria-pressed={full} disabled={fullLoading} onclick={toggleFull}
							title="The outline as the source draws it (every vine parcel), instead of the map's simplified one">
							{fullLoading ? 'Loading…' : 'Full detail'}
						</button>
					</div>
				{/if}
				<div class="seg size">
					<button onclick={() => (mapView.full = !big)} title={big ? 'Back to the page (Esc)' : 'The map full size, the page’s details over it'}
						aria-label={big ? 'Back to the page' : 'Full map'}>{big ? '✕' : '⤢'}</button>
				</div>
				</div>
				<!-- every shape, in columns -->
				<div class="keys">
				{#each keys as k (k.kind + k.id)}
					{@const off = hidden.has(keyOf(k))}
					{@const colour = k.kind === 'appellation' ? cruShade(k.color ?? FALLBACK_REGION, k.cru) : darken(k.color ?? FALLBACK_REGION, (k.cru ?? 0) + 1)}
					{@const c = counts?.[keyOf(k)]}
					<!-- a legend entry: its swatch shows or hides its shape; its name zooms to it (its card open), never
					     another page -->
					<span class="key" class:on={focused(k)} class:off={layers[k.kind] === 'off'} class:hidden={off}>
						<button class="sw" class:vine={k.kind === 'vineyard'} style:--sw={colour} aria-pressed={!off}
							title={off ? `Show ${k.name} on the map` : `Hide ${k.name} from the map`} onclick={() => toggleShown(k)}></button>
						<button class="name" title={focused(k) ? 'Show all' : `Zoom to ${k.name}`} onclick={() => zoomTo(k)}>{k.name}</button>
						{#if c?.tastings}<span class="badge tasted num" title="{c.tastings} tasting{c.tastings > 1 ? 's' : ''}">✎ {c.tastings}</span>{/if}
						{#if c?.bottles}<span class="badge num" title="{c.bottles} bottle{c.bottles > 1 ? 's' : ''} in the cellar">{c.bottles}</span>{/if}
					</span>
				{/each}
				</div>
				{#if missing.length}<span class="missing" title={missing.join(' · ')}>{missing.length} without boundaries</span>{/if}
			</figcaption>
		{/if}
	</figure>
{/snippet}

<style>
	figure {
		margin: 0;
	}
	/* Full size: behind the page's column (app.css: html.map-full main), beside the sidebar; the whole window on a
	   phone, where the page's column is set aside */
	.fullmap.on {
		position: fixed;
		inset: 0 0 0 200px;
		z-index: 40;
		background: var(--bg);
	}
	@media (max-width: 760px) {
		.fullmap.on {
			inset: var(--nav-h, 52px) 0 0 0;
		}
	}
	figure.big {
		position: absolute;
		inset: 0;
		display: flex;
		flex-direction: column;
	}
	figure.big .map {
		flex: 1;
		border-radius: 0;
		border: none;
	}
	/* Full size: the controls and legend a floating card at the bottom right (above the map's credits), the scale
	   beside the page's column */
	figure.big figcaption {
		position: absolute;
		right: 14px;
		bottom: 40px;
		width: min(520px, calc(100% - 600px));
		box-sizing: border-box;
		margin: 0;
		padding: 10px 12px;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 10px;
		box-shadow: var(--shadow);
		z-index: 2;
	}
	figure.big :global(.maplibregl-ctrl-bottom-left) {
		left: 560px;
	}
	@media (max-width: 760px) {
		/* a phone: the page a sheet over the map's lower part (app.css), the controls at the top beside the zoom, the
		   credits and scale just above the sheet */
		figure.big figcaption {
			top: 10px;
			left: 10px;
			right: 54px;
			bottom: auto;
			width: auto;
			padding: 8px 10px;
		}
		figure.big :global(:is(.maplibregl-ctrl-bottom-left, .maplibregl-ctrl-bottom-right)) {
			left: auto;
			bottom: 45dvh;
		}
		figure.big :global(.maplibregl-ctrl-bottom-left) {
			left: 0;
		}
	}
	.size button {
		white-space: nowrap;
	}
	.map {
		position: relative;
		border-radius: 8px;
		overflow: hidden;
		border: 1px solid var(--border);
		background: var(--surface-2);
	}
	.loading {
		position: absolute;
		inset: 0;
		display: grid;
		place-items: center;
		font-size: 13px;
	}
	.bar {
		display: flex;
		align-items: center;
		flex-wrap: wrap;
		gap: 6px;
	}
	.bar .kinds {
		margin-right: auto;
	}
	.seg {
		display: inline-flex;
		border: 1px solid var(--border);
		border-radius: 8px;
		overflow: hidden;
		background: var(--surface);
		font-size: 12px;
	}
	.seg button {
		padding: 4px 9px;
	}
	/* Every shape listed, in columns (a name too long cut, whole on hover); past a few rows the list scrolls */
	.keys {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
		gap: 3px 14px;
		max-height: calc(5 * 1.6em);
		overflow-y: auto;
		overscroll-behavior: contain;
	}
	figure.big .keys {
		max-height: calc(9 * 1.6em);
	}
	@media (max-width: 760px) {
		/* a phone, over the map: a few rows, the rest scrolls */
		figure.big .keys {
			max-height: calc(4 * 1.6em);
		}
	}
	.keys:empty {
		display: none;
	}
	figcaption {
		display: flex;
		flex-direction: column;
		gap: 8px;
		margin-top: 8px;
		font-size: 12px;
		color: var(--muted);
	}
	.key {
		color: inherit;
		display: flex;
		align-items: center;
		gap: 6px;
		min-width: 0;
		line-height: 1.6;
	}
	.key button {
		border: none;
		background: none;
		padding: 0;
		font: inherit;
		color: inherit;
		cursor: pointer;
	}
	.key .name {
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		text-align: left;
	}
	.badge {
		flex: none;
		font-size: 10px;
		font-weight: 600;
		line-height: 1.4;
		color: var(--gold);
		box-shadow: inset 0 0 0 1px var(--gold);
		border-radius: 8px;
		padding: 0 5px;
	}
	.badge.tasted {
		color: var(--accent);
		box-shadow: inset 0 0 0 1px var(--accent);
	}
	.key .name:hover,
	.key.on .name {
		color: var(--text);
	}
	.key.on .name {
		font-weight: 600;
	}
	.key.off {
		opacity: 0.45;
	}
	/* hidden from the map: a hollow swatch, the name struck through */
	.key.hidden .name {
		text-decoration: line-through;
		opacity: 0.6;
	}
	.key .sw {
		position: relative;
		background: var(--sw);
	}
	/* a finger-sized target around the 10 px swatch */
	.key .sw::after {
		content: '';
		position: absolute;
		inset: -7px;
	}
	.key.hidden .sw {
		background: transparent;
		box-shadow: inset 0 0 0 1.5px var(--sw);
	}
	.key .sw:hover {
		outline: 2px solid color-mix(in srgb, var(--sw) 40%, transparent);
	}
	.seg button:disabled {
		cursor: progress;
	}
	.kinds {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
	}
	.sw {
		width: 10px;
		height: 10px;
		border-radius: 3px;
		flex: none;
	}
	/* a vineyard: its darker outline, as on the map */
	.sw.vine {
		box-shadow: inset 0 0 0 1.5px rgb(0 0 0 / 30%);
	}
	.empty {
		display: grid;
		place-items: center;
		padding: 16px;
		border: 1px dashed var(--border);
		border-radius: 8px;
		font-size: 13px;
		text-align: center;
	}
</style>

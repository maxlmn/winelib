<script lang="ts">
	import { goto } from '$app/navigation';
	import WineMap from '#lib/components/WineMap.svelte';
	import type { Basemap, Selection } from '#lib/components/WineMap.svelte';
	import type { Shapes } from '#lib/api/details.ts';
	import { bbox } from '#lib/geo.ts';
	import { links } from '#lib/links.ts';
	import type { MapCollection, MapProps } from '#lib/types.ts';
	import { appSettings } from '#lib/settings.svelte.ts';
	import { cruShade } from '#lib/cru.ts';
	import { FALLBACK_REGION } from '#lib/colors.ts';

	interface Props {
		/** a shapes endpoint (see shapesUrl) */
		src: string;
		/** the page's own appellation / vineyard: the map frames it (no outline, so it reads like its neighbours) */
		current?: Selection;
		height?: number;
		/** shown when there is nothing to draw */
		empty?: string;
		/** with several shapes (a wine's appellation and vineyard), a legend click zooms to that shape instead of opening its page */
		focusable?: boolean;
		/** the page's own shape at full detail (/outline/full), when the shape store has it: a "Full detail" toggle */
		fullUrl?: string | null;
	}

	let { src, current = null, height = 320, empty = 'No boundary data for this one.', focusable = false, fullUrl = null }: Props = $props();

	let shapes = $state<Shapes | null>(null);
	let failed = $state(false);
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
	const drawnApps = $derived(shapes ? swap(shapes.appellations, 'appellation') : null);
	const drawnVines = $derived(shapes ? swap(shapes.vineyards, 'vineyard') : null);

	const outline = $derived(shapes?.region?.features.length ? { ...shapes.region, extent: null } : null);
	const count = $derived((shapes?.appellations.features.length ?? 0) + (shapes?.vineyards.features.length ?? 0));
	const keys = $derived(shapes ? [...shapes.appellations.features, ...shapes.vineyards.features].map((f) => f.properties) : []);
	const missing = $derived(shapes ? [...shapes.appellations.missing, ...shapes.vineyards.missing] : []);

	// The legend's zoomed-to shape (focusable maps); a second click on it frames everything again
	let focus = $state<Selection>(null);
	const canFocus = $derived(focusable && keys.length > 1);
	$effect(() => {
		src;
		focus = null;
	});

	// Frame the page's own shape (or the focused one); its neighbours show around it
	const extent = $derived.by(() => {
		if (outline && !focus) return outline.features[0].properties.bbox; // a region page frames the whole region
		const target = focus ?? current;
		if (!shapes || !target) return null;
		const fc = target.kind === 'appellation' ? shapes.appellations : shapes.vineyards;
		const f = fc.features.find((f) => f.properties.id === target.id);
		return f ? bbox([f.geometry]) : null;
	});
	const fitKey = $derived(focus ? `${src}#${focus.kind}:${focus.id}` : src);
	const focused = (k: MapProps) => focus?.kind === k.kind && focus.id === k.id;

	// Focusable maps with both kinds: appellations and vineyards shown or hidden
	let show = $state({ appellation: true, vineyard: true });
	const bothKinds = $derived(!!(shapes?.appellations.features.length && shapes?.vineyards.features.length));

	// Clicking another shape opens its page
	function open(p: MapProps | null) {
		if (!p || (current && current.kind === p.kind && current.id === p.id)) return;
		goto(p.kind === 'appellation' ? links.appellation(p.id) : links.vineyard(p.id));
	}
</script>

{#if failed || (shapes && !count && !outline)}
	<div class="empty muted" style:min-height="{Math.min(height, 120)}px">
		{#if failed}The map couldn’t load.
		{:else if shapes?.outlines === false}No map outlines installed yet: <a href={`${links.settings()}#maintenance`}>Settings › Maintenance › Map outlines</a> downloads them.
		{:else}{empty}{/if}
	</div>
{:else}
	<figure>
		<div class="map" style:height="{height}px">
			{#if shapes}
				<WineMap
					appellations={drawnApps}
					vineyards={drawnVines}
					selected={focus}
					showAppellations={show.appellation}
					showVineyards={show.vineyard}
					{basemap}
					{fitKey}
					{extent}
					onselect={open}
					pinCard={false}
					regions={outline}
				/>
			{:else}
				<div class="loading muted">Loading map…</div>
			{/if}
		</div>
		{#if shapes}
			<figcaption>
				<div class="seg">
					{#each [['plain', 'Plain'], ['topo', 'Terrain'], ['satellite', 'Satellite']] as [id, label]}
						<button class:on={basemap === id} onclick={() => (basemap = id as Basemap)}>{label}</button>
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
				{#if focusable && bothKinds}
					<div class="seg kinds">
						{#each [['appellation', 'Appellations'], ['vineyard', 'Vineyards']] as [kind, label]}
							<button class:on={show[kind as 'appellation' | 'vineyard']} aria-pressed={show[kind as 'appellation' | 'vineyard']}
								onclick={() => (show[kind as 'appellation' | 'vineyard'] = !show[kind as 'appellation' | 'vineyard'])}>{label}</button>
						{/each}
					</div>
				{/if}
				<div class="keys">
				{#each keys as k (k.kind + k.id)}
					{#if canFocus}
						<button class="key" class:on={focused(k)} class:off={!show[k.kind]} title={focused(k) ? 'Show all' : `Zoom to ${k.name}`}
							onclick={() => { show[k.kind] = true; focus = focused(k) ? null : { kind: k.kind, id: k.id }; }}>
							<span class="sw" class:vine={k.kind === 'vineyard'} style:background={k.kind === 'appellation' ? cruShade(k.color ?? FALLBACK_REGION, k.cru) : k.cru ? cruShade('#3fa66b', k.cru) : undefined}></span>{k.name}
						</button>
					{:else}
						<a class="key" href={k.kind === 'appellation' ? links.appellation(k.id) : links.vineyard(k.id)}>
							<span class="sw" class:vine={k.kind === 'vineyard'} style:background={k.kind === 'appellation' ? cruShade(k.color ?? FALLBACK_REGION, k.cru) : k.cru ? cruShade('#3fa66b', k.cru) : undefined}></span>{k.name}
						</a>
					{/if}
				{/each}
				</div>
				{#if missing.length}<span class="missing" title={missing.join(' · ')}>{missing.length} without boundaries</span>{/if}
			</figcaption>
		{/if}
	</figure>
{/if}

<style>
	figure {
		margin: 0;
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
	.seg {
		order: 1;
		margin-left: auto;
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
	/* Every shape listed; past a few lines the list scrolls */
	.keys {
		flex: 1 1 100%;
		order: 2;
		display: flex;
		flex-wrap: wrap;
		gap: 4px 14px;
		max-height: 4.6em;
		overflow-y: auto;
		overscroll-behavior: contain;
	}
	.missing {
		order: 3;
	}
	figcaption {
		display: flex;
		align-items: center;
		flex-wrap: wrap;
		gap: 4px 14px;
		margin-top: 8px;
		font-size: 12px;
		color: var(--muted);
	}
	.key {
		color: inherit;
		display: inline-flex;
		align-items: center;
		gap: 6px;
	}
	button.key {
		border: none;
		background: none;
		padding: 0;
		font: inherit;
		cursor: pointer;
	}
	button.key:hover,
	button.key.on {
		color: var(--text);
	}
	button.key.on {
		font-weight: 600;
	}
	button.key.off {
		opacity: 0.45;
	}
	.seg.detail {
		margin-left: 0;
	}
	.seg button:disabled {
		cursor: progress;
	}
	.seg.kinds {
		order: 0;
		margin-left: 0;
	}
	.sw {
		width: 10px;
		height: 10px;
		border-radius: 3px;
		flex: none;
	}
	.sw.vine {
		background: #3fa66b;
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

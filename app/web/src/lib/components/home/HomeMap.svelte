<script lang="ts">
	/** The home page's map: the regions you drink from or keep bottles of, in their colours; a click opens its card (and a link to its page).
	 * Opened on `focus` (the latest tasting's wine) when there's one: its vineyard, else its appellation (drawn), else its
	 * region with its neighbours; else on where most of your wine comes from. */
	import { onMount } from 'svelte';
	import { portal } from '#lib/portal.ts';
	import WineMap from '#lib/components/WineMap.svelte';
	import type { Layers } from '#lib/components/WineMap.svelte';
	import { links } from '#lib/links.ts';
	import { appSettings } from '#lib/settings.svelte.ts';
	import { bbox } from '#lib/geo.ts';
	import type { Extent } from '#lib/geo.ts';
	import type { MapCollection, RegionCollection, RegionProps } from '#lib/types.ts';

	interface Focus {
		wineId: number;
		region: string | null;
	}
	/** full: the whole window behind the page (html.map-full in app.css), the page's cards over its left side (over
	 * its lower half on a phone) */
	let { minHeight = 440, focus = null, full = false }: { minHeight?: number; focus?: Focus | null; full?: boolean } = $props();

	$effect(() => {
		document.documentElement.classList.toggle('map-full', full);
		return () => document.documentElement.classList.remove('map-full');
	});
	let winWidth = $state(1024);
	let winHeight = $state(768);
	const phone = $derived(winWidth <= 760);

	// The focused wine's vineyard and appellation (its page's shapes), kept by wine: a wine hovered again isn't asked
	// again, and the map keeps the last one shown while the next is asked (it flies there once it has it)
	type Place = { id: number | null; appellations?: MapCollection; vineyards?: MapCollection };
	type Shapes = Omit<Place, 'id'>;
	const asked = new Map<number, Promise<Shapes>>();
	let place = $state<Place | null>(null);
	$effect(() => {
		const id = focus?.wineId ?? null;
		if (!id) {
			place = { id: null };
			return;
		}
		let stale = false;
		if (!asked.has(id))
			asked.set(id, fetch(`/api/wines/${id}/shapes`).then((r) => (r.ok ? (r.json() as Promise<Shapes>) : {})).catch(() => ({})));
		asked.get(id)!.then((p) => !stale && (place = { ...p, id }));
		return () => (stale = true);
	});
	// the focus's region, as it was when its shapes came (a region-only wine)
	let placeRegion = $state<string | null>(null);
	$effect(() => {
		if (place && place.id === (focus?.wineId ?? null)) placeRegion = focus?.region ?? null;
	});
	const vines = $derived(place?.vineyards?.features.length ? place.vineyards : null);
	const apps = $derived(place?.appellations?.features.length ? place.appellations : null);
	// on a vineyard: it alone filled, its appellation an outline around it
	const layers = $derived<Layers>({ appellation: vines ? 'outline' : 'fill', vineyard: 'fill', lieu: 'outline' });
	// at least `min` degrees across, centred on the box: a speck of a vineyard still shows its slope
	const atLeast = ([w, s, e, n]: Extent, min: number): Extent => {
		const cx = (w + e) / 2, cy = (s + n) / 2;
		const half = Math.max(e - w, n - s, min) / 2;
		return [cx - half, Math.max(cy - half, -85), cx + half, Math.min(cy + half, 85)];
	};

	let overview = $state<RegionCollection | null>(null);
	let failed = $state(false);
	async function load() {
		failed = false;
		try {
			const r = await fetch('/api/map/overview');
			if (!r.ok) throw new Error(String(r.status));
			overview = await r.json();
		} catch {
			failed = true; // it stayed on "Loading the map…" for good
		}
	}
	onMount(load);

	const regions = $derived(
		overview ? { ...overview, features: overview.features.filter((f) => f.properties.bottles > 0 || f.properties.tastings > 0) } : null
	);
	// Fitted to the regions most of your bottles and tastings come from (90%), not every one: a single wine from Canada
	// or China would widen it to the whole world; the whole map without any
	const extent = $derived.by((): Extent | null => {
		// the latest tasting's wine: its vineyard, else its appellation, else its region with its neighbours (~6° across)
		const own = vines ?? apps;
		const ownBox = own ? bbox(own.features.map((f) => f.geometry)) : null;
		if (ownBox) return atLeast(ownBox, vines ? 0.015 : 0.08);
		const focused = placeRegion ? regions?.features.find((f) => f.properties.name === placeRegion)?.properties.bbox : null;
		if (focused) return atLeast(focused, 6);
		const weight = (p: RegionProps) => p.bottles + p.tastings;
		const ranked = (regions?.features ?? []).map((f) => f.properties).sort((a, b) => weight(b) - weight(a));
		const total = ranked.reduce((n, p) => n + weight(p), 0);
		const main: RegionProps[] = [];
		let covered = 0;
		for (const p of ranked) {
			if (covered >= 0.9 * total) break;
			main.push(p);
			covered += weight(p);
		}
		const boxes = main.map((p) => p.bbox).filter((b) => b !== null);
		if (!boxes.length) return overview?.extent ?? null;
		return [Math.min(...boxes.map((b) => b[0])), Math.min(...boxes.map((b) => b[1])), Math.max(...boxes.map((b) => b[2])), Math.max(...boxes.map((b) => b[3]))];
	});
</script>

<svelte:window bind:innerWidth={winWidth} bind:innerHeight={winHeight} />

<div class="home-map" class:full style:min-height={full ? null : `${minHeight}px`} use:portal={full} role="region" aria-label="Your wine map">
	{#if regions && place}
		<WineMap
			{regions}
			regionHref={(r: RegionProps) => links.region(r.name)}
			appellations={apps}
			vineyards={vines}
			{layers}
			selected={null}
			basemap={appSettings.map_default_basemap}
			fitKey="home:{place.id ?? ''}"
			flyMs={900}
			{extent}
			onselect={() => {}}
			worldCopies={false}
			cardSide={full && !phone ? 'right' : 'left'}
			padLeft={full && !phone ? 560 : 0}
			padBottom={full && phone ? Math.round(winHeight * 0.45) : 0}
		/>
	{:else if failed}
		<div class="loading muted">The map couldn’t be loaded. <button type="button" class="link" onclick={load}>Try again</button></div>
	{:else}
		<div class="loading muted">Loading the map…</div>
	{/if}
</div>

<style>
	/* Full size: behind the page's column, beside the sidebar; under the bar and over the tab bar on a phone */
	.home-map.full {
		position: fixed;
		inset: 0 0 0 200px;
		z-index: 40;
		min-height: 0;
		border-radius: 0;
		background: var(--bg);
	}
	/* its scale beside the page's column, not under it */
	.home-map.full :global(.maplibregl-ctrl-bottom-left) {
		left: 560px;
	}
	@media (max-width: 760px) {
		.home-map.full {
			inset: var(--nav-h, 52px) 0 var(--tab-h, 0px) 0;
		}
		/* a phone: the credits and scale just above the cards */
		.home-map.full :global(:is(.maplibregl-ctrl-bottom-left, .maplibregl-ctrl-bottom-right)) {
			left: auto;
			bottom: 45dvh;
		}
		.home-map.full :global(.maplibregl-ctrl-bottom-left) {
			left: 0;
		}
	}
	.home-map {
		position: relative;
		flex: 1;
		border-radius: calc(var(--radius) - 2px);
		overflow: hidden;
	}
	.link {
		background: none;
		border: 0;
		padding: 0 0 0 6px;
		color: var(--accent);
		cursor: pointer;
		font: inherit;
	}
	.loading {
		display: flex;
		align-items: center;
		justify-content: center;
		height: 100%;
		font-size: 13px;
	}
</style>

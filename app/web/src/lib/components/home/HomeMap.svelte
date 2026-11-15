<script lang="ts">
	/** The home page's map: the regions you drink from or keep bottles of, in their colours; a click opens its card (and a link to its page).
	 * Opened on `focus` (the latest tasting's wine) when there's one: its vineyard, else its appellation (drawn), else its
	 * region with its neighbours; else on where most of your wine comes from. */
	import { onMount } from 'svelte';
	import WineMap from '#lib/components/WineMap.svelte';
	import { links } from '#lib/links.ts';
	import { appSettings } from '#lib/settings.svelte.ts';
	import { bbox } from '#lib/geo.ts';
	import type { Extent } from '#lib/geo.ts';
	import type { MapCollection, RegionCollection, RegionProps } from '#lib/types.ts';

	interface Focus {
		wineId: number;
		region: string | null;
	}
	let { minHeight = 440, focus = null }: { minHeight?: number; focus?: Focus | null } = $props();

	// The focused wine's vineyard and appellation (its page's shapes); null while asked, {} when it has none or failed
	let place = $state<{ appellations?: MapCollection; vineyards?: MapCollection } | null>(null);
	$effect(() => {
		const id = focus?.wineId;
		place = id ? null : {};
		if (!id) return;
		let stale = false;
		fetch(`/api/wines/${id}/shapes`)
			.then((r) => (r.ok ? r.json() : {}))
			.catch(() => ({}))
			.then((p) => !stale && (place = p));
		return () => (stale = true);
	});
	const vines = $derived(place?.vineyards?.features.length ? place.vineyards : null);
	const apps = $derived(place?.appellations?.features.length ? place.appellations : null);
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
		const focused = focus?.region ? regions?.features.find((f) => f.properties.name === focus.region)?.properties.bbox : null;
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

<div class="home-map" style:min-height="{minHeight}px">
	{#if regions && place}
		<WineMap
			{regions}
			regionHref={(r: RegionProps) => links.region(r.name)}
			appellations={apps}
			vineyards={vines}
			selected={null}
			basemap={appSettings.map_default_basemap}
			fitKey="home"
			{extent}
			onselect={() => {}}
			worldCopies={false}
		/>
	{:else if failed}
		<div class="loading muted">The map couldn’t be loaded. <button type="button" class="link" onclick={load}>Try again</button></div>
	{:else}
		<div class="loading muted">Loading the map…</div>
	{/if}
</div>

<style>
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

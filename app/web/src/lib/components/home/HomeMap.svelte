<script lang="ts">
	/** The home page's map: the regions you drink from or keep bottles of, in their colours; a click opens its card (and a link to its page).
	 * Opened on `focus` (the latest tasting's region) when there's one, else on where most of your wine comes from. */
	import { onMount } from 'svelte';
	import WineMap from '#lib/components/WineMap.svelte';
	import { links } from '#lib/links.ts';
	import { appSettings } from '#lib/settings.svelte.ts';
	import type { Extent } from '#lib/geo.ts';
	import type { RegionCollection, RegionProps } from '#lib/types.ts';

	let { minHeight = 440, focus = null }: { minHeight?: number; focus?: string | null } = $props();

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
		const focused = focus ? regions?.features.find((f) => f.properties.name === focus)?.properties.bbox : null;
		if (focused) return focused;
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
	{#if regions}
		<WineMap
			{regions}
			regionHref={(r: RegionProps) => links.region(r.name)}
			appellations={null}
			vineyards={null}
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

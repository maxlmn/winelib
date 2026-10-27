<script lang="ts">
	/** The home page's map: the regions you drink from or keep bottles of, in their colours; a click opens the region. */
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import WineMap from '#lib/components/WineMap.svelte';
	import { links } from '#lib/links.ts';
	import { appSettings } from '#lib/settings.svelte.ts';
	import type { Extent } from '#lib/geo.ts';
	import type { RegionCollection, RegionProps } from '#lib/types.ts';

	let { height = 340 }: { height?: number } = $props();

	let overview = $state<RegionCollection | null>(null);
	onMount(async () => {
		overview = await fetch('/api/map/overview').then((r) => r.json());
	});

	const regions = $derived(
		overview ? { ...overview, features: overview.features.filter((f) => f.properties.bottles > 0 || f.properties.tastings > 0) } : null
	);
	// Fitted to your regions (the whole map without any)
	const extent = $derived.by((): Extent | null => {
		const boxes = (regions?.features ?? []).map((f) => f.properties.bbox).filter((b) => b !== null);
		if (!boxes.length) return overview?.extent ?? null;
		return [Math.min(...boxes.map((b) => b[0])), Math.min(...boxes.map((b) => b[1])), Math.max(...boxes.map((b) => b[2])), Math.max(...boxes.map((b) => b[3]))];
	});
</script>

<div class="home-map" style:height="{height}px">
	{#if regions}
		<WineMap
			{regions}
			onregion={(r: RegionProps) => goto(links.region(r.name))}
			appellations={null}
			vineyards={null}
			selected={null}
			basemap={appSettings.map_default_basemap}
			fitKey="home"
			{extent}
			onselect={() => {}}
		/>
	{:else}
		<div class="loading muted">Loading the map…</div>
	{/if}
</div>

<style>
	.home-map {
		position: relative;
		border-radius: calc(var(--radius) - 2px);
		overflow: hidden;
	}
	.loading {
		display: flex;
		align-items: center;
		justify-content: center;
		height: 100%;
		font-size: 13px;
	}
</style>

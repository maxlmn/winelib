<script lang="ts">
	import WineMap from '#lib/components/WineMap.svelte';
	import type { Shapes } from '#lib/api/details.ts';
	import { bbox } from '#lib/geo.ts';

	/** A suggestion's map before it's linked (Maintenance › Lieux-dits for your wines): the wine's appellation, the
	 * suggested lieu-dit as its vineyard, the lieux-dits around it. `src`: a wine's shapes with ?lieu_dit= */
	let { src }: { src: string } = $props();

	let shapes = $state<Shapes | null>(null);
	let failed = $state(false);
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
	// framed on the lieu-dit with room around it (its neighbours, the village's name), not the whole appellation
	const extent = $derived.by(() => {
		const b = shapes ? bbox(shapes.vineyards.features.map((f) => f.geometry).filter((g) => !!g)) : null;
		if (!b) return null;
		const [w, s, e, n] = b;
		const dx = Math.max(e - w, 0.004) * 1.2, dy = Math.max(n - s, 0.003) * 1.2;
		return [w - dx, s - dy, e + dx, n + dy] as typeof b;
	});
</script>

<div class="peek">
	{#if shapes}
		<WineMap appellations={shapes.appellations} vineyards={shapes.vineyards} selected={null} basemap="plain"
			fitKey={src} {extent} onselect={() => {}} pinCard={false} />
	{:else}
		<div class="muted msg">{failed ? 'Couldn’t load the map.' : 'Loading map…'}</div>
	{/if}
</div>

<style>
	.peek {
		position: relative;
		height: 280px;
		margin: 6px 0 10px 26px;
		border: 1px solid var(--border);
		border-radius: 8px;
		overflow: hidden;
	}
	.msg {
		padding: 12px;
		font-size: 13px;
	}
</style>

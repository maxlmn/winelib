<script lang="ts">
	import CellarCards from '#lib/components/CellarCards.svelte';
	import type { Bottle, RegionColors } from '#lib/types.ts';

	interface Props {
		bottles: Bottle[];
		regionColors: RegionColors;
		empty?: string;
		/** one wine's bottles: plain cards (CellarCards) */
		plain?: boolean;
		/** the bottle whose page this is (CellarCards) */
		current?: number | null;
	}

	let { bottles, regionColors, empty = 'Nothing in the cellar.', plain = false, current = null }: Props = $props();

	const OPEN_UP_TO = 30;
	let wrap = $state<HTMLDivElement>();

	// The cellar page opens only its first card; a detail page holds a few lines, so show them all
	$effect(() => {
		if (wrap && bottles.length <= OPEN_UP_TO) wrap.querySelectorAll('details').forEach((d) => (d.open = true));
	});
</script>

{#if bottles.length}
	<div bind:this={wrap}><CellarCards {bottles} {regionColors} {plain} {current} /></div>
{:else}
	<p class="muted">{empty}</p>
{/if}

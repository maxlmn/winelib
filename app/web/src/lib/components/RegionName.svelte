<script lang="ts">
	import { regionColor, regionLabel } from '#lib/regions.svelte.ts';

	/** A region as text: its colour's dot, then "Mosel, Germany". */
	let { name }: { name: string | null | undefined } = $props();
</script>

{#if name}<span class="region-name"><span class="dot" style:background={regionColor(name)}></span>{regionLabel(name)}</span>{/if}

<style>
	.region-name {
		white-space: nowrap;
	}
	.dot {
		display: inline-block;
		width: 8px;
		height: 8px;
		border-radius: 50%;
		margin-right: 5px;
		vertical-align: 0.05em;
	}
</style>

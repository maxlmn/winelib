<script lang="ts">
	import { FALLBACK_REGION, typeColor } from '#lib/colors.ts';
	import { regionColor } from '#lib/regions.svelte.ts';

	/** A list's progress as bottle ends, one per entry: filled in its region's colour once tasted (the wine's colour as
	 * the cork), a ring until then; a ring with a cork dot when owned but not yet tasted. */
	import type { Dot } from '#lib/api/lists.ts';

	let { dots, size = 14 }: { dots: Dot[]; size?: number } = $props();
</script>

<span class="dots" style:--d="{size}px" aria-hidden="true">
	{#each dots as d, i (i)}
		<span
			class="dot"
			class:tasted={d.tasted}
			style:--region={regionColor(d.region) ?? FALLBACK_REGION}
			style:--wine={d.color ? typeColor(d.color) : 'transparent'}
		>{#if d.tasted || d.owned}<span class="cork"></span>{/if}</span>
	{/each}
</span>

<style>
	.dots {
		display: flex;
		flex-wrap: wrap;
		gap: 4px;
	}
	.dot {
		width: var(--d);
		height: var(--d);
		border-radius: 50%;
		box-sizing: border-box;
		border: 2px solid var(--region);
		display: inline-flex;
		align-items: center;
		justify-content: center;
	}
	.dot.tasted {
		background: var(--region);
		border-color: color-mix(in srgb, var(--region) 70%, #000);
	}
	.cork {
		width: calc(var(--d) * 0.36);
		height: calc(var(--d) * 0.36);
		border-radius: 50%;
		background: var(--wine);
	}
</style>

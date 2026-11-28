<script lang="ts">
	/** A wine's colour as a mark: a dot in its colour, or small bubbles for the sparkling ones (a dot alone reads as a
	 *  white or a rosé). The name on hover */
	import { typeColor } from '#lib/colors.ts';

	let { color, size = 10, title = true }: { color: string | null | undefined; size?: number; title?: boolean } = $props();
	const bubbles = $derived((color ?? '').startsWith('Bubbles'));
</script>

{#if bubbles}
	<svg class="bubbles" viewBox="0 0 14 14" width={Math.round(size * 1.4)} height={Math.round(size * 1.4)} fill={typeColor(color)} stroke="rgba(0,0,0,0.25)" stroke-width="0.6" role="img" aria-label={color}>
		{#if title}<title>{color}</title>{/if}
		<circle cx="4.5" cy="9.5" r="3.6" /><circle cx="10.2" cy="6" r="2.5" /><circle cx="6" cy="2.6" r="1.8" />
	</svg>
{:else}
	<span class="dot" style:background={typeColor(color)} style:width="{size}px" style:height="{size}px" style:align-self="center" title={title ? (color ?? undefined) : undefined}></span>
{/if}

<style>
	.bubbles {
		display: inline-block;
		flex: none;
		vertical-align: middle;
	}
</style>

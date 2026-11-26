<script lang="ts">
	import PillToggle from './PillToggle.svelte';
	import type { LayerMode } from '#lib/components/WineMap.svelte';

	/** A kind of shape on a map (appellations, vineyards, lieux-dits): a click cycles filled → outline only →
	 * hidden; its swatch shows which. */
	interface Props {
		label: string;
		mode: LayerMode;
		/** the swatch's colour (a plain colour: an outline is drawn in it too) */
		swatch?: string;
		/** a dashed outline (the lieux-dits) */
		dashed?: boolean;
		/** after the label, muted ("1 of 82 drawn") */
		note?: string;
	}
	let { label, mode = $bindable(), swatch = '#9a9893', dashed = false, note }: Props = $props();

	const next: Record<LayerMode, LayerMode> = { fill: 'outline', outline: 'off', off: 'fill' };
	const says: Record<LayerMode, string> = { fill: 'filled', outline: 'outline only', off: 'hidden' };
</script>

<PillToggle off={mode === 'off'} onclick={() => (mode = next[mode])} label="{label}: {says[mode]}"
	title="{label}: {says[mode]} (click: {says[next[mode]]})">
	<span class="sw {mode}" class:dashed style:--sw={swatch}></span>
	{label}{#if note}<span class="muted note">{note}</span>{/if}
</PillToggle>

<style>
	.sw {
		width: 11px;
		height: 11px;
		border-radius: 3px;
		flex: none;
		background: var(--sw);
		border: 1.5px solid transparent;
	}
	/* outline only: the swatch's colour as its edge, nothing inside */
	.sw.outline {
		background: none;
		border: 2px solid var(--sw);
	}
	.sw.dashed {
		background: none;
		border: 1.5px dashed currentColor;
	}
	.sw.fill.dashed {
		background: color-mix(in srgb, currentColor 30%, transparent);
	}
	.sw.off {
		opacity: 0.35;
		background:
			linear-gradient(to top right, transparent calc(50% - 1px), currentColor calc(50% - 1px), currentColor calc(50% + 1px), transparent calc(50% + 1px));
		border: 1.5px solid currentColor;
	}
	.note {
		margin-left: 2px;
	}
</style>

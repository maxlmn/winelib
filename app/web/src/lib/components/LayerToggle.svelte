<script lang="ts">
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

<button class="toggle {mode}" onclick={() => (mode = next[mode])} aria-label="{label}: {says[mode]}"
	title="{label}: {says[mode]} (click: {says[next[mode]]})">
	<span class="sw" class:dashed style:--sw={swatch}></span>
	{label}{#if note}<span class="muted note">{note}</span>{/if}
</button>

<style>
	.toggle {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		padding: 4px 9px;
		border: 1px solid var(--border);
		border-radius: 999px;
		background: var(--surface);
		color: inherit;
		font: inherit;
		font-size: 12px;
		cursor: pointer;
		white-space: nowrap;
	}
	.toggle:hover {
		border-color: var(--accent);
	}
	.toggle.off {
		color: var(--muted);
	}
	.toggle.off .sw {
		opacity: 0.35;
	}
	.sw {
		width: 11px;
		height: 11px;
		border-radius: 3px;
		flex: none;
		background: var(--sw);
		border: 1.5px solid transparent;
	}
	/* outline only: the swatch's colour as its edge, nothing inside */
	.outline .sw {
		background: none;
		border: 2px solid var(--sw);
	}
	.sw.dashed {
		background: none;
		border: 1.5px dashed currentColor;
	}
	.fill .sw.dashed {
		background: color-mix(in srgb, currentColor 30%, transparent);
	}
	.off .sw {
		background:
			linear-gradient(to top right, transparent calc(50% - 1px), currentColor calc(50% - 1px), currentColor calc(50% + 1px), transparent calc(50% + 1px));
		border: 1.5px solid currentColor;
	}
	.note {
		margin-left: 2px;
	}
</style>

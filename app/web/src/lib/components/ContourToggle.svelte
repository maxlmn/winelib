<script lang="ts">
	/** Beside the layers of a map: the contour lines inside the vineyards (contours.svelte.ts), on or off */
	import { contours, setContours } from '#lib/contours.svelte.ts';
</script>

<button class="toggle" class:off={!contours.on} aria-pressed={contours.on} onclick={() => setContours(!contours.on)}
	title={contours.on ? 'Inside the vineyards: their slope shaded from the bottom to the top, and contour lines (click: hide)' : 'Inside the vineyards: their slope shaded from the bottom to the top, and contour lines (click: show)'}>
	<svg class="sw" viewBox="0 0 16 11" aria-hidden="true">
		<path d="M1 9 C5 7, 9 9, 15 6 M1 5.5 C5 3.5, 9 5.5, 15 2.5" fill="none" stroke="currentColor" stroke-width="1.2" />
	</svg>
	Contours
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
		width: 16px;
		height: 11px;
		flex: none;
	}
</style>

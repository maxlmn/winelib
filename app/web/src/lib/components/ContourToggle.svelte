<script lang="ts">
	/** Beside the layers of a map: the contour lines and slope shading inside the vineyards (contours.svelte.ts) */
	import { contours, setContours } from '#lib/contours.svelte.ts';
	import PillToggle from './PillToggle.svelte';
</script>

<PillToggle off={!contours.on} pressed={contours.on} onclick={() => setContours(!contours.on)}
	title="Inside the vineyards: their slope shaded from the bottom to the top, and contour lines (click: {contours.on ? 'hide' : 'show'})">
	<svg class="sw" class:faded={!contours.on} viewBox="0 0 16 11" aria-hidden="true">
		<path d="M1 9 C5 7, 9 9, 15 6 M1 5.5 C5 3.5, 9 5.5, 15 2.5" fill="none" stroke="currentColor" stroke-width="1.2" />
	</svg>
	Contours
</PillToggle>

<style>
	.sw {
		width: 16px;
		height: 11px;
		flex: none;
	}
	.faded {
		opacity: 0.35;
	}
</style>

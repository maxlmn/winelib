<script lang="ts">
	/** The label shown by a line's pips while hovered (labelTip.svelte.ts): one for the whole app, in the layout */
	import { labelTipState } from '#lib/labelTip.svelte.ts';

	const tip = $derived(labelTipState.tip);
</script>

{#if tip}
	<div class="label-tip" class:below={tip.below} style:left="{tip.x}px" style:top="{tip.y}px" aria-hidden="true">
		<img src={tip.src} alt="" decoding="async" />
	</div>
{/if}

<style>
	/* framed like a print, over the page, the pointer passing through it */
	.label-tip {
		position: fixed;
		z-index: 60;
		transform: translate(-50%, calc(-100% - 8px));
		padding: 4px;
		background: #fff;
		border: 1px solid var(--border);
		border-radius: 4px;
		box-shadow: var(--shadow);
		pointer-events: none;
	}
	.label-tip.below {
		transform: translate(-50%, 8px);
	}
	img {
		display: block;
		max-width: 200px;
		max-height: 150px;
	}
</style>

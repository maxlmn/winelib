<script lang="ts">
	import NoteText from './NoteText.svelte';

	/** A note shown as written (its Markdown), folded to a few lines when long, "Show all" to unfold it. */
	let { md, lines = 6 }: { md: string; lines?: number } = $props();

	let open = $state(false);
	let long = $state(false);
	let box = $state<HTMLDivElement>();
	$effect(() => {
		void md;
		if (box) long = box.scrollHeight > box.clientHeight + 4;
	});
</script>

<div class="fold" class:open class:long bind:this={box} style:--lines={lines}>
	<NoteText {md} />
</div>
{#if long || open}
	<button type="button" class="more" onclick={() => (open = !open)} aria-expanded={open}>{open ? 'Show less' : 'Show all'}</button>
{/if}

<style>
	.fold {
		max-height: calc(var(--lines) * 1.5em);
		overflow: hidden;
		font-size: 13px;
		line-height: 1.5;
	}
	.fold.long:not(.open) {
		mask-image: linear-gradient(to bottom, #000 55%, transparent);
	}
	.fold.open {
		max-height: none;
	}
	.more {
		padding: 0;
		border: none;
		background: none;
		color: var(--accent);
		font: inherit;
		font-size: 12px;
		cursor: pointer;
	}
	/* folded, a menu's headings stay small */
	.fold :global(h1),
	.fold :global(h2),
	.fold :global(h3),
	.fold :global(h4) {
		font-size: 11px;
		margin: 6px 0 2px;
	}
</style>

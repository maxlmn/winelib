<script lang="ts">
	import { links } from '#lib/links.ts';
	import type { BottleShelf } from '#lib/api/details.ts';

	/** A bottle's place as a mini shelf map: its storage group's bins in shelf order, each filled as far as it holds
	 * against its capacity, the bottle's bin highlighted; a bin opens the cellar's shelf map on it. */
	let { shelf }: { shelf: BottleShelf } = $props();

	const fill = (b: BottleShelf['bins'][number]) => (b.capacity ? Math.min(1, b.qty / b.capacity) : b.qty ? 1 : 0);
</script>

<div class="shelf" aria-label="{shelf.group}: where it is">
	<div class="bins">
		{#each shelf.bins as b (b.name)}
			<a class="bin" class:here={b.here} class:empty={!b.qty} href={links.cellar({ loc: b.name, view: 'shelves' })}
				title="{b.name}: {b.qty} bottle{b.qty === 1 ? '' : 's'}{b.capacity ? ` of ${b.capacity}` : ''}{b.here ? ' · this bottle' : ''}">
				<span class="level" style:height="{Math.round(fill(b) * 100)}%"></span>
				<span class="name">{b.name}</span>
			</a>
		{/each}
	</div>
</div>

<style>
	.bins {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(34px, 1fr));
		gap: 4px;
		max-width: 420px;
	}
	.bin {
		position: relative;
		height: 30px;
		border: 1px solid var(--border);
		border-radius: 4px;
		background: var(--surface-2);
		overflow: hidden;
		text-decoration: none;
		color: var(--muted);
	}
	.bin:hover {
		border-color: var(--accent);
	}
	/* how full the bin is: from the bottom, as bottles stack */
	.level {
		position: absolute;
		left: 0;
		right: 0;
		bottom: 0;
		background: color-mix(in srgb, var(--muted) 30%, transparent);
	}
	.name {
		position: relative;
		display: block;
		text-align: center;
		font-size: 10px;
		line-height: 30px;
		font-variant-numeric: tabular-nums;
	}
	.bin.here {
		border: 2px solid var(--accent);
		color: var(--text);
		font-weight: 600;
	}
	.bin.here .level {
		background: color-mix(in srgb, var(--accent) 45%, transparent);
	}
	.bin.empty .name {
		opacity: 0.6;
	}
</style>

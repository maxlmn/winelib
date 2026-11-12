<script lang="ts">
	/** A cuvée's uploaded labels, small and side by side (one per different image, newest vintage first); hovered or
	 * clicked, a label opens larger in a pop-up with the vintages that have it */
	import { photoSrc } from '#lib/api/photos.ts';

	interface Props {
		labels: { url: string; vintages: string[] }[];
		/** the cuvée's name, for the images' descriptions */
		name: string;
	}

	let { labels, name }: Props = $props();

	let open = $state<number | null>(null);
	// a click keeps it open (a phone has no hover): hover alone closes it when the pointer leaves
	let pinned = $state(false);
	let root = $state<HTMLElement>();

	const src = (url: string, size: 'thumb' | 'large') => (/\.svg(\?|$)/i.test(url) ? url : photoSrc(url, size));
	const vintages = (l: { vintages: string[] }) => (l.vintages.length > 3 ? `${l.vintages.at(-1)}–${l.vintages[0]}` : l.vintages.join(', '));

	function toggle(i: number) {
		if (open === i && pinned) {
			open = null;
			pinned = false;
		} else {
			open = i;
			pinned = true;
		}
	}
	function outside(e: PointerEvent) {
		if (open !== null && root && !root.contains(e.target as Node)) {
			open = null;
			pinned = false;
		}
	}
	function key(e: KeyboardEvent) {
		if (e.key === 'Escape' && open !== null) {
			open = null;
			pinned = false;
		}
	}
</script>

<svelte:window onpointerdown={outside} onkeydown={key} />

{#if labels.length}
	<span class="thumbs" bind:this={root}>
		{#each labels as l, i (l.url)}
			<span
				class="thumb-wrap"
				role="presentation"
				onpointerenter={(e) => e.pointerType === 'mouse' && !pinned && (open = i)}
				onpointerleave={(e) => e.pointerType === 'mouse' && !pinned && (open = null)}
			>
				<button
					type="button"
					class="thumb"
					aria-expanded={open === i}
					aria-label="The {vintages(l)} label of {name}"
					onclick={() => toggle(i)}
				>
					<img src={src(l.url, 'thumb')} alt="" loading="lazy" decoding="async" />
				</button>
				{#if open === i}
					<span class="pop" role="dialog" aria-label="The {vintages(l)} label of {name}">
						<a href={l.url} target="_blank" rel="noopener" title="Open the label full size">
							<img src={src(l.url, 'large')} alt="The {vintages(l)} label of {name}" decoding="async" />
						</a>
						<span class="muted">{vintages(l)}</span>
					</span>
				{/if}
			</span>
		{/each}
	</span>
{/if}

<style>
	.thumbs {
		display: inline-flex;
		flex-wrap: nowrap;
		gap: 4px;
		flex: none;
	}
	.thumb-wrap {
		position: relative;
		display: inline-flex;
	}
	.thumb {
		display: block;
		padding: 0;
		border: 1px solid var(--border);
		border-radius: 3px;
		background: var(--surface);
		cursor: zoom-in;
		overflow: hidden;
	}
	.thumb:hover,
	.thumb[aria-expanded='true'] {
		border-color: var(--accent);
	}
	.thumb img {
		display: block;
		height: 34px;
		width: auto;
		max-width: 64px;
		object-fit: cover;
	}
	/* the label larger, under its thumbnail, over the list: its right edge on the thumbnail's (the thumbnails sit at
	   the right of the line, so it opens toward the page, not off it) */
	.pop {
		position: absolute;
		z-index: 30;
		top: calc(100% + 6px);
		right: 0;
		display: flex;
		flex-direction: column;
		gap: 4px;
		width: max-content;
		max-width: min(320px, calc(100vw - 32px));
		padding: 8px;
		border: 1px solid var(--border);
		border-radius: 8px;
		background: var(--surface);
		box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);
		font-size: 12px;
		text-align: center;
	}
	.pop img {
		display: block;
		max-width: 100%;
		max-height: 260px;
		margin: 0 auto;
		border-radius: 3px;
	}
</style>

<script lang="ts">
	/** A cuvée's uploaded labels, small and side by side (one per different image, newest vintage first); hovered or
	 * clicked, a label opens larger in a pop-up with the vintages that have it */
	import { photoSrc } from '#lib/api/photos.ts';
	import { opensImage } from '#lib/lightbox.svelte.ts';

	interface Props {
		labels: { url: string; vintages: string[] }[];
		/** the cuvée's name, for the images' descriptions */
		name: string;
		/** the pop-up's side: its right edge on the thumbnail's (thumbnails at a line's end), else its left edge */
		align?: 'left' | 'right';
		/** a strip of the column's width, the labels side by side in it, slid left and right (‹ ›) when they don't fit */
		carousel?: boolean;
	}

	let { labels, name, align = 'right', carousel = false }: Props = $props();

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
	// the carousel: its arrows shown when there's more that way
	let track = $state<HTMLElement>();
	let canLeft = $state(false);
	let canRight = $state(false);
	function edges() {
		if (!track) return;
		canLeft = track.scrollLeft > 1;
		canRight = track.scrollLeft + track.clientWidth < track.scrollWidth - 1;
	}
	function slide(dir: number) {
		track?.scrollBy({ left: dir * track.clientWidth * 0.8, behavior: 'smooth' });
	}
	$effect(() => {
		void labels.length;
		edges();
	});
	function key(e: KeyboardEvent) {
		if (e.key === 'Escape' && open !== null) {
			open = null;
			pinned = false;
		}
	}
</script>

<svelte:window onpointerdown={outside} onkeydown={key} />

{#if labels.length}
	{@const shown = open !== null ? labels[open] : null}
	<!-- the pop-up outside the strip (it would be clipped in it): under the thumbnails, on their side -->
	<span
		class="thumbs"
		class:carousel
		bind:this={root}
		role="presentation"
		onpointerleave={(e) => e.pointerType === 'mouse' && !pinned && (open = null)}
	>
		<span class="track" bind:this={track} onscroll={edges}>
			{#each labels as l, i (l.url)}
				<button
					type="button"
					class="thumb"
					aria-expanded={open === i}
					aria-label="The {vintages(l)} label of {name}"
					onpointerenter={(e) => e.pointerType === 'mouse' && !pinned && (open = i)}
					onclick={() => toggle(i)}
				>
					<img src={src(l.url, 'thumb')} alt="" loading="lazy" decoding="async" onload={edges} />
				</button>
			{/each}
		</span>
		{#if carousel && canLeft}<button type="button" class="arrow prev" aria-label="Previous labels" onclick={() => slide(-1)}>‹</button>{/if}
		{#if carousel && canRight}<button type="button" class="arrow next" aria-label="More labels" onclick={() => slide(1)}>›</button>{/if}
		{#if shown}
			<span class="pop" class:left={align === 'left'} role="dialog" aria-label="The {vintages(shown)} label of {name}">
				<a href={shown.url} use:opensImage={{ src: src(shown.url, 'large'), alt: `The ${vintages(shown)} label of ${name}` }} title="Open the label full size">
					<img src={src(shown.url, 'large')} alt="The {vintages(shown)} label of {name}" decoding="async" />
				</a>
				<span class="muted">{vintages(shown)}</span>
			</span>
		{/if}
	</span>
{/if}

<style>
	.thumbs {
		position: relative;
		display: inline-flex;
		align-self: flex-start;
		flex: none;
		max-width: 100%;
	}
	/* the thumbnails their own height, whatever the line's (a cuvée's vintages opened beside them) */
	.track {
		display: inline-flex;
		align-items: flex-start;
		flex-wrap: nowrap;
		gap: 4px;
	}
	/* the carousel: the column's width, slid sideways, each label snapping to its edge */
	.thumbs.carousel {
		display: flex;
		width: 100%;
	}
	.carousel .track {
		display: flex;
		width: 100%;
		overflow-x: auto;
		scroll-snap-type: x mandatory;
		scrollbar-width: none;
		overscroll-behavior-x: contain;
	}
	.carousel .track::-webkit-scrollbar {
		display: none;
	}
	.carousel .thumb {
		flex: none;
		scroll-snap-align: start;
	}
	/* fewer than fit: at the column's right */
	.carousel .thumb:first-child {
		margin-left: auto;
	}
	.arrow {
		position: absolute;
		top: 50%;
		transform: translateY(-50%);
		display: grid;
		place-items: center;
		width: 18px;
		height: 22px;
		padding: 0;
		border: 1px solid var(--border);
		border-radius: 4px;
		background: color-mix(in srgb, var(--surface) 92%, transparent);
		box-shadow: 0 1px 4px rgba(0, 0, 0, 0.15);
		color: var(--text);
		font-size: 15px;
		line-height: 1;
		cursor: pointer;
	}
	.arrow:hover {
		color: var(--accent);
		border-color: var(--accent);
	}
	.prev {
		left: -4px;
	}
	.next {
		right: -4px;
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
		height: 48px;
		width: auto;
		max-width: 90px;
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
	.pop.left {
		right: auto;
		left: 0;
	}
	.pop img {
		display: block;
		max-width: 100%;
		max-height: 260px;
		margin: 0 auto;
		border-radius: 3px;
	}
</style>

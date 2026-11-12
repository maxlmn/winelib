<script lang="ts">
	/** The image opened from a page (lightbox.open, use:opensImage), whole, over a dimmed page: a click outside it, ✕
	 * or Esc closes it */
	import { lightbox } from '#lib/lightbox.svelte.ts';
	import { afterNavigate } from '$app/navigation';

	afterNavigate(() => lightbox.close());
	function key(e: KeyboardEvent) {
		if (e.key === 'Escape' && lightbox.shown) lightbox.close();
	}
</script>

<svelte:window onkeydown={key} />

{#if lightbox.shown}
	{@const s = lightbox.shown}
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<div class="lightbox" role="dialog" aria-modal="true" aria-label={s.alt || 'Image'} tabindex="-1" onclick={(e) => e.target === e.currentTarget && lightbox.close()}>
		<figure>
			<img src={s.src} alt={s.alt} decoding="async" />
			{#if s.alt}<figcaption>{s.alt}</figcaption>{/if}
		</figure>
		<button type="button" class="close" onclick={() => lightbox.close()} aria-label="Close (Esc)" title="Close (Esc)">✕</button>
	</div>
{/if}

<style>
	.lightbox {
		position: fixed;
		inset: 0;
		z-index: 1000;
		display: grid;
		place-items: center;
		padding: 24px;
		background: rgba(20, 18, 16, 0.82);
		cursor: zoom-out;
	}
	figure {
		margin: 0;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 8px;
		max-width: 100%;
		max-height: 100%;
		cursor: default;
	}
	img {
		display: block;
		max-width: min(1400px, calc(100vw - 48px));
		max-height: calc(100vh - 96px);
		max-height: calc(100dvh - 96px);
		object-fit: contain;
		border-radius: 6px;
		box-shadow: 0 12px 40px rgba(0, 0, 0, 0.45);
		background: #fff;
	}
	figcaption {
		color: #f2efe8;
		font-size: 13px;
		text-align: center;
	}
	.close {
		position: absolute;
		top: 14px;
		right: 14px;
		width: 36px;
		height: 36px;
		border: none;
		border-radius: 50%;
		background: rgba(255, 255, 255, 0.15);
		color: #fff;
		font-size: 17px;
		cursor: pointer;
	}
	.close:hover {
		background: rgba(255, 255, 255, 0.3);
	}
</style>

<script lang="ts">
	import Icon from '#lib/components/Icon.svelte';
	import { sessionSticker, tastingSticker, toBlob, type Style, type StickerWine } from '#lib/shareCard.ts';

	/** Share a tasting as a sticker for a story (Instagram...): this wine, or the whole evening; a transparent PNG with
	 * light or dark text, or a solid card. Share opens the phone's share sheet; else it downloads. */
	let { wine, session, when, where, filename }: { wine: StickerWine; session: StickerWine[]; when: string; where: string; filename: string } =
		$props();

	let open = $state(false);
	let what = $state<'wine' | 'session'>('wine');
	let style = $state<Style>('light');
	let backdrop = $state<'photo' | 'light'>('photo');
	let error = $state('');

	const canvas = $derived(
		open ? (what === 'session' && session.length > 1 ? sessionSticker(session, when, where, style) : tastingSticker(wine, when, where, style)) : null
	);
	const src = $derived(canvas?.toDataURL('image/png') ?? '');
	const name = $derived(`${filename}${what === 'session' ? '-session' : ''}.png`);
	const canShare = typeof navigator !== 'undefined' && !!navigator.canShare;

	async function share() {
		error = '';
		if (!canvas) return;
		try {
			const file = new File([await toBlob(canvas)], name, { type: 'image/png' });
			if (navigator.canShare?.({ files: [file] })) await navigator.share({ files: [file] });
			else download();
		} catch (e) {
			if ((e as Error)?.name !== 'AbortError') error = 'Couldn’t share it: download it instead';
		}
	}
	function download() {
		const a = Object.assign(document.createElement('a'), { href: src, download: name });
		a.click();
	}
</script>

<button class="btn icon" onclick={() => (open = true)} title="Share as a sticker" aria-label="Share as a sticker"><Icon name="share" size={15} /></button>

{#if open}
	<div class="backdrop" role="presentation" onclick={(e) => e.target === e.currentTarget && (open = false)}>
		<div class="sheet card" role="dialog" aria-modal="true" aria-label="Share as a sticker">
			<div class="head">
				<h2>Share as a sticker</h2>
				<button class="close" onclick={() => (open = false)} aria-label="Close">✕</button>
			</div>
			<div class="controls">
				{#if session.length > 1}
					<div class="seg" role="group" aria-label="What">
						<button class:on={what === 'wine'} onclick={() => (what = 'wine')}>This wine</button>
						<button class:on={what === 'session'} onclick={() => (what = 'session')}>The session · {session.length}</button>
					</div>
				{/if}
				<div class="seg" role="group" aria-label="Style">
					<button class:on={style === 'light'} onclick={() => (style = 'light')}>White text</button>
					<button class:on={style === 'dark'} onclick={() => (style = 'dark')}>Dark text</button>
					<button class:on={style === 'card'} onclick={() => (style = 'card')}>Card</button>
				</div>
			</div>
			<!-- What it looks like on a photo (a dark one, or a bright one); the PNG itself is transparent -->
			<div class="preview" class:bright={backdrop === 'light'}>
				{#if src}<img {src} alt="The sticker" />{/if}
			</div>
			<div class="foot">
				<label class="muted small"><input type="checkbox" checked={backdrop === 'light'} onchange={(e) => (backdrop = e.currentTarget.checked ? 'light' : 'photo')} /> Preview on a bright photo</label>
				{#if error}<span class="error">{error}</span>{/if}
				<button class="btn" onclick={download}>Download PNG</button>
				{#if canShare}<button class="btn primary" onclick={share}>Share…</button>{/if}
			</div>
			<p class="muted small hint">On a phone, Share sends it to Instagram (or anywhere): add it to your story over a photo, then move and size it there.</p>
		</div>
	</div>
{/if}

<style>
	.backdrop {
		position: fixed;
		inset: 0;
		z-index: 50;
		background: rgba(0, 0, 0, 0.55);
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 16px;
	}
	.sheet {
		width: min(560px, 100%);
		max-height: calc(100vh - 32px);
		overflow: auto;
		padding: 18px;
		display: flex;
		flex-direction: column;
		gap: 12px;
	}
	.head {
		display: flex;
		align-items: center;
	}
	h2 {
		margin: 0;
		font-size: 17px;
	}
	.close {
		margin-left: auto;
		border: none;
		background: none;
		font-size: 18px;
		cursor: pointer;
		color: var(--muted);
	}
	.controls {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
	}
	.seg {
		display: inline-flex;
		border: 1px solid var(--border);
		border-radius: 8px;
		overflow: hidden;
	}
	.seg button {
		border: none;
		background: none;
		padding: 6px 11px;
		font-size: 13px;
		cursor: pointer;
		color: var(--muted);
	}
	.seg button.on {
		background: var(--accent);
		color: #fff;
	}
	.preview {
		border-radius: 12px;
		padding: 18px;
		/* a photo's tones behind it: dark by default, bright when asked */
		background: linear-gradient(135deg, #3a2f2a, #6b5345 45%, #2b2421);
	}
	.preview.bright {
		background: linear-gradient(135deg, #f3ebe2, #dccab6 50%, #efe6dc);
	}
	.preview img {
		display: block;
		width: 100%;
		height: auto;
	}
	.foot {
		display: flex;
		align-items: center;
		gap: 8px;
		flex-wrap: wrap;
	}
	.foot label {
		margin-right: auto;
		display: flex;
		align-items: center;
		gap: 6px;
	}
	.small {
		font-size: 12px;
	}
	.hint {
		margin: 0;
	}
	.error {
		color: var(--down);
		font-size: 12px;
	}
</style>

<script lang="ts">
	/** A wine's label at the top of its page (Settings > Labels): the one uploaded for it (a photo, a scan, a drawing),
	 * else the nearest vintage's of the cuvée; nothing when none is. Uploading, replacing, removing: the page's ⋯ menu
	 * (pick, remove), or an image dropped on the label (anywhere on the page while it has none). Under it, the labels
	 * kept aside from wines merged into it: to use in its place, or remove */
	import { invalidateAll } from '$app/navigation';
	import { ask, tell } from '#lib/ask.svelte.ts';
	import { LABEL_TYPES, MAX_PHOTO_MB, deleteLabel, deleteSpareLabel, photoSrc, uploadLabel, useSpareLabel } from '#lib/api/photos.ts';
	import { appSettings } from '#lib/settings.svelte.ts';
	import { opensImage } from '#lib/lightbox.svelte.ts';

	interface Props {
		wineId: number;
		producer: string;
		cuvee: string;
		/** the appellation's name, else the region's */
		place: string | null | undefined;
		vintage: string;
		/** the uploaded label: this vintage's, else (from_vintage) another vintage's of the cuvée */
		uploaded?: { url: string; from_vintage: string | null } | null;
		/** labels kept aside from wines merged into this one */
		spares?: { name: string; url: string }[];
	}

	let { wineId, producer, cuvee, place, vintage, uploaded = null, spares = [] }: Props = $props();

	// Without a label, an image dragged over the page: dropped anywhere, it's the wine's label
	let over = $state(false);
	const hasFile = (e: DragEvent) => !!e.dataTransfer?.types.includes('Files');
	const anywhere = $derived(appSettings.wine_labels !== 'off' && !uploaded);
	function pageOver(e: DragEvent) {
		if (!anywhere || !hasFile(e)) return;
		e.preventDefault();
		over = true;
	}
	function pageLeave(e: DragEvent) {
		if (!e.relatedTarget) over = false; // left the window
	}
	function pageDrop(e: DragEvent) {
		if (!anywhere || !hasFile(e)) return;
		e.preventDefault();
		over = false;
		put(e.dataTransfer?.files[0]);
	}

	async function spare(name: string, use: boolean) {
		if (!use && !(await ask('It can’t be brought back.', { title: 'Remove this kept label?', confirmLabel: 'Remove', danger: true }))) return;
		busy = use ? 'Changing…' : 'Removing…';
		try {
			await (use ? useSpareLabel : deleteSpareLabel)(wineId, name);
			await invalidateAll();
		} catch (e) {
			await tell(e instanceof Error ? e.message : String(e), use ? 'The label wasn’t changed' : 'The label wasn’t removed');
		} finally {
			busy = '';
		}
	}
	const isSvg = (url: string) => /\.svg(\?|$)/i.test(url);

	let input = $state<HTMLInputElement>();
	let busy = $state('');
	let dragging = $state(false);

	/** The file picker (the page's ⋯ menu: Upload its label) */
	export function pick() {
		input?.click();
	}

	async function put(file: File | undefined | null) {
		if (!file) return;
		if (!LABEL_TYPES.includes(file.type)) return tell('Use a JPEG, PNG, WebP or SVG image.', 'Not a label WineLib can keep');
		if (file.size > MAX_PHOTO_MB * 1024 * 1024) return tell(`Labels can be up to ${MAX_PHOTO_MB} MB.`, 'This image is too large');
		busy = 'Uploading…';
		try {
			await uploadLabel(wineId, file);
			await invalidateAll();
		} catch (e) {
			await tell(e instanceof Error ? e.message : String(e), 'The label wasn’t saved');
		} finally {
			busy = '';
			if (input) input.value = '';
		}
	}

	/** The uploaded label removed, once confirmed (the page's ⋯ menu: Remove its label) */
	export async function remove() {
		const ok = await ask('The nearest vintage’s label, or none, is shown in its place.', { title: 'Remove this label?', confirmLabel: 'Remove', danger: true });
		if (!ok) return;
		busy = 'Removing…';
		try {
			await deleteLabel(wineId);
			await invalidateAll();
		} catch (e) {
			await tell(e instanceof Error ? e.message : String(e), 'The label wasn’t removed');
		} finally {
			busy = '';
		}
	}

	const name = $derived(`Label: ${[producer, cuvee, place, vintage].filter(Boolean).join(', ')}`);
	const large = $derived(uploaded ? (/\.svg(\?|$)/i.test(uploaded.url) ? uploaded.url : photoSrc(uploaded.url, 'large')) : '');
</script>

<svelte:window ondragover={pageOver} ondragleave={pageLeave} ondrop={pageDrop} />

{#if appSettings.wine_labels !== 'off'}
	{#if over}<div class="drop-here" aria-hidden="true"><span>Drop the image: this wine’s label</span></div>{/if}
	<input bind:this={input} type="file" accept={LABEL_TYPES.join(',')} hidden onchange={(e) => put(e.currentTarget.files?.[0])} />
	{#if uploaded}
		<div
			class="wine-label"
			class:dragging
			role="group"
			aria-label="The wine’s label"
			ondragover={(e) => (e.preventDefault(), (dragging = true))}
			ondragleave={() => (dragging = false)}
			ondrop={(e) => (e.preventDefault(), (dragging = false), put(e.dataTransfer?.files[0]))}
		>
			<a class="label photo" href={uploaded.url} use:opensImage={{ src: large, alt: name }} title="Open the label full size">
				<img src={large} alt={name} decoding="async" />
			</a>
			{#if uploaded.from_vintage || busy}
				<div class="tools">
					{#if uploaded.from_vintage}<span class="muted">The {uploaded.from_vintage}’s label</span>{/if}
					{#if busy}<span class="muted" role="status">{busy}</span>{/if}
				</div>
			{/if}
		</div>
	{:else if busy}
		<span class="muted small" role="status">{busy}</span>
	{/if}
	{#if spares.length}
		<div class="spares">
			<span class="muted">Kept from {spares.length > 1 ? 'wines' : 'a wine'} merged into this one</span>
			{#each spares as s (s.name)}
				<div class="spare">
					<a href={s.url} use:opensImage={{ src: isSvg(s.url) ? s.url : photoSrc(s.url, 'large'), alt: 'A label kept from a merged wine' }} title="Open it full size">
						<img src={isSvg(s.url) ? s.url : photoSrc(s.url, 'thumb')} alt="A label kept from a merged wine" loading="lazy" decoding="async" />
					</a>
					<button type="button" class="link" disabled={!!busy} onclick={() => spare(s.name, true)}>Use this one</button>
					<button type="button" class="link" disabled={!!busy} onclick={() => spare(s.name, false)}>Remove</button>
				</div>
			{/each}
		</div>
	{/if}
{/if}

<style>
	/* the header column's width, the label centred in it */
	.wine-label {
		align-self: stretch;
		min-width: 0;
	}
	.wine-label.dragging .label {
		outline: 2px dashed var(--accent);
		outline-offset: 3px;
	}
	.tools {
		display: flex;
		flex-wrap: wrap;
		justify-content: center;
		gap: 4px 14px;
		margin-top: 6px;
		font-size: 12px;
	}
	.small {
		font-size: 12px;
	}
	/* an image dragged over the page of a wine without a label */
	.drop-here {
		position: fixed;
		inset: 0;
		z-index: 900;
		display: grid;
		place-items: center;
		background: color-mix(in srgb, var(--accent) 14%, transparent);
		outline: 3px dashed var(--accent);
		outline-offset: -10px;
		pointer-events: none;
	}
	.drop-here span {
		padding: 10px 16px;
		border-radius: 8px;
		background: var(--surface);
		box-shadow: var(--shadow);
		font-size: 14px;
	}
	/* the labels kept aside from a merge */
	.spares {
		align-self: stretch;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 6px;
		font-size: 12px;
	}
	.spare {
		display: flex;
		align-items: center;
		gap: 12px;
	}
	.spare img {
		display: block;
		height: 48px;
		max-width: 90px;
		object-fit: cover;
		border: 1px solid var(--border);
		border-radius: 3px;
	}
	.link {
		padding: 0;
		border: none;
		background: none;
		font: inherit;
		color: var(--accent);
		cursor: pointer;
	}
	.link:disabled {
		color: var(--muted);
		cursor: default;
	}
	/* the label: up to the card's width (never enlarged past its own size), centred, not too tall */
	.photo {
		display: block;
		width: fit-content;
		max-width: 100%;
		margin: 0 auto;
		cursor: zoom-in;
	}
	.photo img {
		display: block;
		max-width: 100%;
		max-height: 420px;
		border-radius: 3px;
	}
</style>

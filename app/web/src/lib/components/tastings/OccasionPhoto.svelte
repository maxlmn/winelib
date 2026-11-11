<script lang="ts">
	/** The evening's photo where it's shown (a tasting's page): added, replaced or removed there and then, without
	 * opening the tasting's form. Photos are filed by place and day (app/api/photos.py), so it's the occasion's: every
	 * wine of that evening there shows it. */
	import { invalidateAll } from '$app/navigation';
	import { ask, tell } from '#lib/ask.svelte.ts';
	import { MAX_PHOTO_MB, PHOTO_TYPES, deletePhoto, photoSrc, uploadPhoto } from '#lib/api/photos.ts';

	interface Props {
		/** the place's name (or the free-text location) and the day it's filed under */
		place: string | null | undefined;
		date: string | null | undefined;
		/** the photo there is, its full-size URL */
		url: string | null | undefined;
		alt: string;
	}

	let { place, date, url, alt }: Props = $props();

	let input = $state<HTMLInputElement>();
	let busy = $state('');
	let dragging = $state(false);

	async function put(file: File | undefined | null) {
		if (!file || !place || !date) return;
		if (!PHOTO_TYPES.includes(file.type)) return tell('Use a JPEG, PNG, WebP or GIF image.', 'Not a photo WineLib can keep');
		if (file.size > MAX_PHOTO_MB * 1024 * 1024) return tell(`Photos can be up to ${MAX_PHOTO_MB} MB.`, 'This photo is too large');
		busy = url ? 'Replacing…' : 'Adding…';
		try {
			await uploadPhoto(place, date, file);
			await invalidateAll();
		} catch (e) {
			await tell(e instanceof Error ? e.message : String(e), 'The photo wasn’t saved');
		} finally {
			busy = '';
			if (input) input.value = '';
		}
	}

	async function remove() {
		if (!place || !date) return;
		if (!(await ask('The photo of this evening is removed for every wine of it.', { title: 'Remove the photo?', confirmLabel: 'Remove', danger: true }))) return;
		busy = 'Removing…';
		try {
			await deletePhoto(place, date);
			await invalidateAll();
		} catch (e) {
			await tell(e instanceof Error ? e.message : String(e), 'The photo wasn’t removed');
		} finally {
			busy = '';
		}
	}
</script>

{#if place && date}
	<!-- a phone offers its camera and its photos -->
	<input bind:this={input} type="file" accept={PHOTO_TYPES.join(',')} hidden onchange={(e) => put(e.currentTarget.files?.[0])} />
	{#if url}
		<figure>
			<a class="shot" href={url} target="_blank" rel="noopener" title="Open the full-size photo">
				<img src={photoSrc(url, 'large')} {alt} decoding="async" />
			</a>
			<figcaption>
				<button type="button" class="link" onclick={() => input?.click()} disabled={!!busy}>Replace the photo</button>
				<button type="button" class="link" onclick={remove} disabled={!!busy}>Remove</button>
				{#if busy}<span class="muted" role="status">{busy}</span>{/if}
			</figcaption>
		</figure>
	{:else}
		<button
			type="button"
			class="add"
			class:dragging
			onclick={() => input?.click()}
			ondragover={(e) => (e.preventDefault(), (dragging = true))}
			ondragleave={() => (dragging = false)}
			ondrop={(e) => (e.preventDefault(), (dragging = false), put(e.dataTransfer?.files[0]))}
			disabled={!!busy}
		>
			{busy || '＋ Add a photo of the evening'}
			<span class="muted small">or drop one here</span>
		</button>
	{/if}
{/if}

<style>
	figure {
		margin: 14px 0 0;
	}
	.shot {
		display: block;
		width: fit-content;
		cursor: zoom-in;
	}
	img {
		display: block;
		max-width: 100%;
		max-height: 420px;
		border-radius: 8px;
	}
	figcaption {
		display: flex;
		align-items: baseline;
		gap: 14px;
		margin-top: 6px;
		font-size: 12px;
	}
	.link {
		border: 0;
		background: none;
		padding: 0;
		font: inherit;
		color: var(--muted);
		cursor: pointer;
	}
	.link:hover {
		color: var(--accent);
	}
	.add {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 2px;
		width: 100%;
		margin-top: 14px;
		padding: 18px 12px;
		border: 1.5px dashed var(--border);
		border-radius: 8px;
		background: none;
		color: var(--text);
		font: inherit;
		cursor: pointer;
	}
	.add:hover,
	.add.dragging {
		border-color: var(--accent);
		color: var(--accent);
	}
	.small {
		font-size: 12px;
	}
</style>

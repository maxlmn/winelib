<script lang="ts">
	import { MAX_PHOTO_MB, PHOTO_TYPES, photoFor, photoSrc } from '#lib/api/photos.ts';

	interface Props {
		/** photos are filed by place name and date */
		place: string | null | undefined;
		date: string;
		file: File | null;
		remove: boolean;
	}

	let { place, date, file = $bindable(null), remove = $bindable(false) }: Props = $props();

	let current = $state<string | null>(null);
	let error = $state('');
	let dragging = $state(false);
	let input = $state<HTMLInputElement>();
	let root = $state<HTMLDivElement>();
	// Not a form input event: tell the form it changed (unsaved-changes guard). Fired on the wrapper, not the
	// file input, whose own change handler would otherwise run again.
	const touched = () => root?.dispatchEvent(new Event('change', { bubbles: true }));

	// The photo already filed for this place and day (it follows date / place changes)
	$effect(() => {
		current = null;
		if (!place || !date) return;
		let cancelled = false;
		photoFor(place, date).then((url) => !cancelled && (current = url));
		return () => (cancelled = true);
	});

	const preview = $derived(file ? URL.createObjectURL(file) : null);
	$effect(() => () => {
		if (preview) URL.revokeObjectURL(preview);
	});

	// The current photo as its small copy: the original can be several MB
	const shown = $derived(preview ?? (remove || !current ? null : photoSrc(current, 'thumb')));

	function pick(f: File | undefined | null) {
		error = '';
		if (!f) return;
		if (!PHOTO_TYPES.includes(f.type)) return void (error = 'Use a JPEG, PNG, WebP or GIF image');
		if (f.size > MAX_PHOTO_MB * 1024 * 1024) return void (error = `Photos can be up to ${MAX_PHOTO_MB} MB`);
		file = f;
		remove = false;
		touched();
	}

	function clear() {
		if (file) file = null;
		else remove = true;
		if (input) input.value = '';
		touched();
	}
</script>

<div class="photo" bind:this={root}>
	<span class="label">Photo of the evening</span>
	{#if !place}
		<p class="muted hint">Pick the place first: photos are filed by place and date.</p>
	{:else}
		<div
			class="zone"
			class:dragging
			class:has={shown}
			role="button"
			tabindex="0"
			aria-label="Choose a photo"
			onclick={() => input?.click()}
			onkeydown={(e) => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), input?.click())}
			ondragover={(e) => (e.preventDefault(), (dragging = true))}
			ondragleave={() => (dragging = false)}
			ondrop={(e) => (e.preventDefault(), (dragging = false), pick(e.dataTransfer?.files[0]))}
		>
			{#if shown}
				<img src={shown} alt="Photo of {place} on {date}" />
				<span class="badge">{file ? 'New photo, saved with the note' : 'Current photo · click to replace'}</span>
			{:else}
				<span class="empty">
					<b>＋ Add a photo</b>
					<span class="muted">Drop an image here, or click to choose{remove ? ' (current photo will be removed)' : ''}</span>
				</span>
			{/if}
		</div>
		<input bind:this={input} type="file" accept={PHOTO_TYPES.join(',')} hidden onchange={(e) => pick(e.currentTarget.files?.[0])} />
		<div class="row">
			{#if shown}<button type="button" class="link" onclick={clear}>{file ? 'Undo' : 'Remove photo'}</button>{/if}
			{#if remove && current && !file}<button type="button" class="link" onclick={() => (remove = false)}>Keep current photo</button>{/if}
			<span class="muted hint">{error ? '' : 'One photo per place and day, shared by its notes and visits'}</span>
			{#if error}<span class="error">{error}</span>{/if}
		</div>
	{/if}
</div>

<style>
	.photo {
		display: flex;
		flex-direction: column;
		gap: 6px;
	}
	.label {
		font-size: 12px;
		font-weight: 600;
		color: var(--muted);
	}
	.zone {
		position: relative;
		display: flex;
		align-items: center;
		justify-content: center;
		min-height: 110px;
		border: 1.5px dashed var(--border);
		border-radius: 10px;
		background: var(--surface-2);
		cursor: pointer;
		overflow: hidden;
		transition: border-color 0.15s, background 0.15s;
	}
	.zone:hover,
	.zone:focus-visible,
	.zone.dragging {
		border-color: var(--accent);
		background: var(--accent-soft);
		outline: none;
	}
	.zone.has {
		border-style: solid;
		min-height: 0;
	}
	img {
		display: block;
		max-width: 100%;
		max-height: 280px;
		object-fit: contain;
	}
	.badge {
		position: absolute;
		left: 8px;
		bottom: 8px;
		padding: 2px 8px;
		border-radius: 10px;
		background: color-mix(in srgb, #000 55%, transparent);
		color: #fff;
		font-size: 11px;
	}
	.empty {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 4px;
		font-size: 13px;
		text-align: center;
		padding: 0 12px;
	}
	.row {
		display: flex;
		align-items: center;
		gap: 12px;
		flex-wrap: wrap;
	}
	.link {
		border: none;
		background: none;
		padding: 0;
		color: var(--accent);
		cursor: pointer;
		font-size: 13px;
	}
	.hint {
		font-size: 12px;
		margin: 0;
	}
	.error {
		color: var(--down);
		font-size: 12px;
	}
</style>

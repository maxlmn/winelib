<script lang="ts">
	/** A wine's label at the top of its page (Settings > Labels): the one uploaded for it (a photo, a scan, a drawing),
	 * else, when chosen, one drawn from what WineLib knows of it: the same frame for every wine, in its pip's colours
	 * (the region's, the wine's), with the outline of where it comes from (its appellation, else its region; else the
	 * producer's initials) */
	import { invalidateAll } from '$app/navigation';
	import { ask, tell } from '#lib/ask.svelte.ts';
	import { LABEL_TYPES, MAX_PHOTO_MB, deleteLabel, photoSrc, uploadLabel } from '#lib/api/photos.ts';
	import { appSettings } from '#lib/settings.svelte.ts';
	import { FALLBACK_REGION, typeColor } from '#lib/colors.ts';

	interface Props {
		wineId: number;
		producer: string;
		cuvee: string;
		/** the appellation's name, else the region's */
		place: string | null | undefined;
		vintage: string;
		color: string | null | undefined;
		shape: { d: string; of: string } | null | undefined;
		/** the uploaded label: this vintage's, else (from_vintage) another vintage's of the cuvée */
		uploaded?: { url: string; from_vintage: string | null } | null;
		/** the region's colour (its pips') */
		region?: string | null;
	}

	let { wineId, producer, cuvee, place, vintage, color, shape, uploaded = null, region = null }: Props = $props();

	const mode = $derived(appSettings.wine_labels ?? 'drawn');
	let input = $state<HTMLInputElement>();
	let busy = $state('');
	let dragging = $state(false);

	/** The file picker (also the page's ⋯ menu: Upload its label) */
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
		const ok = await ask('The drawn label, or none, is shown in its place.', { title: 'Remove this label?', confirmLabel: 'Remove', danger: true });
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

	// The colours of its pip (BottleEnd): the region's on the band and the frame, the wine's in the outline
	const regionInk = $derived(region || FALLBACK_REGION);
	const fill = $derived(color ? typeColor(color) : '#b4b2a9');

	// The initials, the house's words left out: "Domaine Roulot" R, "Egon Müller" EM
	const SKIP = new Set(['domaine', 'dom', 'château', 'chateau', 'maison', 'weingut', 'bodegas', 'tenuta', 'cave', 'caves', 'clos',
		'et', 'and', 'und', 'y', 'e', 'de', 'du', 'des', 'la', 'le', 'les', "l'", 'von', 'van', 'di', 'del', 'fils', 'père', 'frères']);
	const initials = $derived.by(() => {
		const words = producer.split(/[\s-]+/).filter((w) => w && !SKIP.has(w.toLowerCase()));
		const use = words.length ? words : producer.split(/\s+/);
		return use.slice(0, 2).map((w) => w.replace(/^[^\p{L}]+/u, '')[0]?.toUpperCase() ?? '').join('');
	});
	const name = $derived(`Label: ${[producer, cuvee, place, vintage].filter(Boolean).join(', ')}`);
</script>

{#if mode !== 'off'}
	<input bind:this={input} type="file" accept={LABEL_TYPES.join(',')} hidden onchange={(e) => put(e.currentTarget.files?.[0])} />
	{#if uploaded || mode === 'drawn'}
		<div
			class="wine-label"
			class:dragging
			role="group"
			aria-label="The wine’s label"
			ondragover={(e) => (e.preventDefault(), (dragging = true))}
			ondragleave={() => (dragging = false)}
			ondrop={(e) => (e.preventDefault(), (dragging = false), put(e.dataTransfer?.files[0]))}
		>
			{#if uploaded}
				<a class="label photo" href={uploaded.url} target="_blank" rel="noopener" title="Open the label full size">
					<img src={/\.svg(\?|$)/i.test(uploaded.url) ? uploaded.url : photoSrc(uploaded.url, 'large')} alt={name} decoding="async" />
				</a>
			{:else}
				<figure class="label drawn" style:--region={regionInk} style:--fill={fill} role="img" aria-label={name}>
					<div class="frame">
						{#if shape}
							<svg class="emblem" viewBox="0 0 100 100" aria-hidden="true"><path d={shape.d} /></svg>
						{:else}
							<div class="crest" aria-hidden="true">{initials}</div>
						{/if}
						<div class="text">
							<div class="producer">{producer}</div>
							{#if cuvee}<div class="cuvee">{cuvee}</div>{/if}
							{#if place}<div class="place">{place}</div>{/if}
							{#if vintage}<div class="year num">{vintage}</div>{/if}
						</div>
					</div>
				</figure>
			{/if}
			<!-- uploading, replacing, removing: the page's ⋯ menu (pick, remove) -->
			{#if uploaded?.from_vintage || busy}
				<div class="tools">
					{#if uploaded?.from_vintage}<span class="muted">The {uploaded.from_vintage}’s label</span>{/if}
					{#if busy}<span class="muted" role="status">{busy}</span>{/if}
				</div>
			{/if}
		</div>
	{:else if busy}
		<span class="muted small" role="status">{busy}</span>
	{/if}
{/if}

<style>
	/* the header column's width, the label centred in it: its own size on a computer, the card's width on a phone */
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
		gap: 4px 14px;
		margin-top: 6px;
		font-size: 12px;
	}
	.small {
		font-size: 12px;
	}
	/* an uploaded label: within the drawn one's box on a computer; on a phone up to the card's width (never enlarged
	   past its own size) */
	.photo {
		display: block;
		width: fit-content;
		max-width: 100%;
		margin: 0 auto;
		cursor: zoom-in;
	}
	.photo img {
		display: block;
		max-width: min(300px, 100%);
		max-height: 220px;
		border-radius: 3px;
	}
	/* a drawn label: wider than tall, as on a bottle */
	.drawn.label {
		width: 300px;
		max-width: 100%;
		margin: 0 auto;
		container-type: inline-size;
		aspect-ratio: 3 / 2;
		box-sizing: border-box;
		border-radius: 3px;
		overflow: hidden;
	}
	.drawn {
		/* the region's colour, darkened enough to read on the paper (England's white, Champagne's pale gold) */
		--ink: color-mix(in srgb, var(--region) 50%, #2c2c2a);
		padding: 7px;
		/* paper: the same in light and dark */
		background: #f6f1e6;
		border-top: 8px solid var(--region);
		box-shadow: inset 0 0 0 1px rgba(44, 44, 42, 0.08);
		color: #2c2c2a;
		font-family: 'Iowan Old Style', 'Palatino Linotype', Palatino, 'Book Antiqua', Georgia, serif;
		text-align: center;
	}
	/* the outline at the left, the words at the right */
	.frame {
		height: 100%;
		box-sizing: border-box;
		display: flex;
		align-items: center;
		gap: 4cqi;
		padding: 2.6cqi 4.6cqi;
		border: 1px solid color-mix(in srgb, var(--ink) 55%, transparent);
		border-radius: 2px;
	}
	.text {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 1px;
	}
	.emblem {
		width: 28cqi;
		height: 28cqi;
		flex: none;
	}
	.emblem path {
		fill: var(--fill);
		stroke: var(--ink);
		stroke-width: 1.4;
		stroke-linejoin: round;
		vector-effect: non-scaling-stroke;
		fill-rule: evenodd;
	}
	.crest {
		display: grid;
		place-items: center;
		flex: none;
		width: 21cqi;
		height: 21cqi;
		margin: 0 3.3cqi;
		border: 1.5px solid var(--ink);
		border-radius: 50%;
		color: var(--ink);
		font-size: 7.3cqi;
		letter-spacing: 0.04em;
	}
	.producer {
		font-size: 5cqi;
		line-height: 1.2;
		overflow-wrap: anywhere;
	}
	.cuvee {
		font-size: 4.2cqi;
		font-style: italic;
		line-height: 1.2;
		overflow-wrap: anywhere;
	}
	.place {
		margin-top: 2cqi;
		font-size: 3.2cqi;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--ink);
		line-height: 1.3;
	}
	.year {
		margin-top: 1.3cqi;
		font-size: 5.3cqi;
	}
	/* a phone: the card's width, the drawn label's type and outline growing with it */
	@media (max-width: 560px) {
		.drawn.label {
			width: 100%;
		}
		.photo img {
			max-width: 100%;
			max-height: 420px;
		}
	}
</style>

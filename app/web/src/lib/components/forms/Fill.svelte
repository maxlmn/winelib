<script lang="ts">
	import { emptyWine, newVintageDraft } from '#lib/api/forms.ts';
	import type { BottleDraft, Choice, Options, WineDraft, WineForm, WineSummary } from '#lib/api/forms.ts';
	import { request, messageOf } from '#lib/api/http.ts';
	import { links } from '#lib/links.ts';

	/** Fill the bottle form from text or from photos: an order or auction email, an invoice or a producer's sheet
	 * pasted in (POST /api/lookups/from-text), or photos of the labels, the front and the back, read by Claude
	 * (POST /api/lookups/from-photos; with an Anthropic API key). Either fills the wine (the one in WineLib, a new
	 * vintage of a cuvée it knows, or a new wine); the text also the quantity, the price a bottle, the date and the
	 * vendor. A draft to check, nothing saved. */
	interface Props {
		wine: WineSummary | null;
		draft: WineDraft | null;
		details: BottleDraft;
		qty: number | null;
		options: Options;
	}
	let { wine = $bindable(), draft = $bindable(), details = $bindable(), qty = $bindable(), options }: Props = $props();

	interface Found {
		line: string;
		producer: Choice | null;
		cuvee: string;
		vintage: string;
		type: string | null;
		size: string | null;
		appellation: Choice | null;
		region: Choice | null;
		wine_id: number | null;
		/** a vintage of the same cuvée in WineLib: a new vintage starts from it */
		like_id: number | null;
		qty: number | null;
		price: number | null;
		currency: string | null;
		/** the lot's or order's price as written, when the price a bottle was worked out from it */
		price_total: number | null;
		purchase_date: string | null;
		vendor: string | null;
		/** from photos: the labels' disgorgement date, what couldn't be read, a word for the person checking */
		disgorgement_date?: string | null;
		not_read?: string[];
		note?: string | null;
	}

	type Side = 'front' | 'back';
	interface Photo {
		media_type: string;
		data: string;
		/** its thumbnail */
		url: string;
	}

	let mode = $state<'text' | 'photos' | null>(null);
	let text = $state('');
	let photos = $state<Record<Side, Photo | null>>({ front: null, back: null });
	let busy = $state(false);
	let error = $state('');
	let found = $state<Found | null>(null);
	let how = $state('');

	function close() {
		mode = null;
		found = null;
		error = '';
	}

	async function fill(read: () => Promise<Found>) {
		if (busy) return;
		busy = true;
		error = '';
		try {
			apply(await read());
		} catch (e) {
			found = null;
			error = messageOf(e);
		} finally {
			busy = false;
		}
	}

	async function apply(f: Found) {
		if (f.wine_id) {
			wine = (await request<WineForm>(`/api/forms/wines/${f.wine_id}`)).summary;
			draft = null;
			how = 'already in WineLib';
		} else {
			let d: WineDraft;
			if (f.like_id) {
				d = newVintageDraft(await request<WineForm>(`/api/forms/wines/${f.like_id}`));
				how = f.disgorgement_date && f.vintage === 'NV' ? 'another disgorgement of a cuvée you have' : 'a new vintage of a cuvée you have';
			} else {
				d = emptyWine(f.producer);
				how = f.producer?.id ? 'a new cuvée' : 'a new wine';
			}
			d.vintage = f.vintage || d.vintage;
			if (f.disgorgement_date) d.disgorgement_date = f.disgorgement_date;
			if (!f.like_id) {
				if (f.cuvee) d.cuvee = f.cuvee;
				if (f.type) d.type = f.type;
				if (f.appellation) d.appellation = f.appellation;
				if (f.region) d.region = f.region;
			}
			draft = d;
			wine = null;
		}
		if (f.qty) qty = f.qty;
		if (f.price !== null) details.price = f.price;
		if (f.currency && options.currencies.includes(f.currency)) details.currency = f.currency;
		if (f.purchase_date) details.purchase_date = f.purchase_date;
		if (f.vendor) details.vendor = f.vendor;
		if (f.size && options.bottle_sizes.includes(f.size)) details.bottle_size = f.size;
		found = f;
	}

	const fromText = () => request<Found>('/api/lookups/from-text', { method: 'POST', body: { text } });
	const fromPhotos = () =>
		request<Found>('/api/lookups/from-photos', {
			method: 'POST',
			body: { photos: (['front', 'back'] as Side[]).flatMap((side) => (photos[side] ? [{ side, media_type: photos[side]!.media_type, data: photos[side]!.data }] : [])) }
		});

	// A photo shrunk on the phone before it's sent: ~1600 px is sharp enough for a label's small print, and quick
	// to send over a mobile connection
	const MAX_SIDE = 1600;
	async function shrink(file: File): Promise<Photo> {
		const url = URL.createObjectURL(file);
		const img = new Image();
		img.src = url;
		await img.decode();
		const scale = Math.min(1, MAX_SIDE / Math.max(img.naturalWidth, img.naturalHeight));
		const canvas = document.createElement('canvas');
		canvas.width = Math.round(img.naturalWidth * scale);
		canvas.height = Math.round(img.naturalHeight * scale);
		canvas.getContext('2d')!.drawImage(img, 0, 0, canvas.width, canvas.height);
		const jpeg = canvas.toDataURL('image/jpeg', 0.85);
		return { media_type: 'image/jpeg', data: jpeg.slice(jpeg.indexOf(',') + 1), url };
	}

	async function pick(side: Side, e: Event) {
		const input = e.currentTarget as HTMLInputElement;
		const file = input.files?.[0];
		input.value = '';
		if (!file) return;
		error = '';
		try {
			drop(side);
			photos[side] = await shrink(file);
		} catch {
			error = 'That photo couldn’t be opened';
		}
	}

	function drop(side: Side) {
		if (photos[side]) URL.revokeObjectURL(photos[side]!.url);
		photos[side] = null;
	}

	const FIELD_NAMES: Record<string, string> = { cuvee: 'cuvée', disgorgement: 'disgorgement date' };
</script>

<div class="fill">
	{#if !mode}
		<div class="links">
			{#if options.label_photos}<button type="button" class="link" onclick={() => (mode = 'photos')}>Fill from photos of the labels</button>{/if}
			<button type="button" class="link" onclick={() => (mode = 'text')}>Fill from text: an order or auction email, an invoice…</button>
		</div>
	{:else if mode === 'text'}
		<label for="b-text">Fill from text</label>
		<textarea id="b-text" rows="5" bind:value={text} placeholder="Paste the email or invoice: the wine, quantity, price, date and vendor are read from it"></textarea>
		<div class="row">
			<button type="button" class="btn" onclick={() => fill(fromText)} disabled={busy || !text.trim()}>{busy ? 'Reading…' : 'Fill'}</button>
			<button type="button" class="link" onclick={close}>Close</button>
		</div>
	{:else}
		<span class="title">Fill from photos</span>
		<div class="photos">
			{#each ['front', 'back'] as const as side (side)}
				<div class="slot">
					<label class="shot" class:empty={!photos[side]} aria-label={side === 'front' ? 'Photo of the front label' : 'Photo of the back label'}>
						{#if photos[side]}<img src={photos[side]!.url} alt="" />{:else}<span>{side === 'front' ? 'Front' : 'Back'}<small>{side === 'back' ? 'optional' : 'label'}</small></span>{/if}
						<input type="file" accept="image/*" hidden onchange={(e) => pick(side, e)} />
					</label>
					{#if photos[side]}<button type="button" class="remove" aria-label="Remove the {side} photo" onclick={() => drop(side)}>×</button>{/if}
				</div>
			{/each}
		</div>
		<p class="muted small hint">The back label often has what the front leaves out: the producer, the appellation, the disgorgement. The photos are sent to Anthropic to be read.</p>
		<div class="row">
			<button type="button" class="btn" onclick={() => fill(fromPhotos)} disabled={busy || (!photos.front && !photos.back)}>{busy ? 'Reading the labels…' : 'Fill'}</button>
			<button type="button" class="link" onclick={close}>Close</button>
		</div>
	{/if}
	{#if mode && error}<p class="error">{error}</p>{/if}
	{#if mode && found}
		<div class="found">
			Read “{found.line}”: {how}{#if found.wine_id} (<a href={links.wine(found.wine_id)}>open it</a>){/if}.
			{[
				found.qty ? `${found.qty} × ` : '',
				found.price !== null ? `${found.price.toLocaleString()} ${found.currency ?? ''} a bottle` : '',
				found.price_total ? ` (${found.price_total.toLocaleString()} for the lot)` : '',
				found.purchase_date ? ` · ${found.purchase_date}` : '',
				found.vendor ? ` · ${found.vendor}` : ''
			].join('')}
			{#if found.disgorgement_date}Disgorged {found.disgorgement_date}.{/if}
			{#if found.not_read?.length}Not read: {found.not_read.map((f) => FIELD_NAMES[f] ?? f).join(', ')}.{/if}
			{#if found.note}{found.note}{/if}
			Check the fields below.
		</div>
	{/if}
</div>

<style>
	.fill {
		display: flex;
		flex-direction: column;
		gap: 6px;
		margin-bottom: 12px;
	}
	.links {
		display: flex;
		flex-wrap: wrap;
		gap: 4px 18px;
	}
	label,
	.title {
		font-size: 13px;
		font-weight: 600;
	}
	textarea {
		width: 100%;
		font: inherit;
		font-size: 13px;
		resize: vertical;
	}
	.photos {
		display: flex;
		gap: 10px;
	}
	.slot {
		position: relative;
	}
	.shot {
		display: grid;
		place-items: center;
		width: 108px;
		height: 144px;
		border-radius: 8px;
		overflow: hidden;
		cursor: pointer;
		background: var(--surface-2);
		font-weight: 500;
	}
	.shot.empty {
		border: 1.5px dashed var(--border);
		color: var(--muted);
	}
	.shot span {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 2px;
	}
	.shot small {
		font-size: 11px;
		font-weight: 400;
	}
	.shot img {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}
	.remove {
		position: absolute;
		top: 4px;
		right: 4px;
		width: 24px;
		height: 24px;
		border: none;
		border-radius: 50%;
		background: rgb(0 0 0 / 0.55);
		color: #fff;
		font-size: 16px;
		line-height: 1;
		cursor: pointer;
	}
	.hint {
		margin: 0;
	}
	.row {
		display: flex;
		gap: 12px;
		align-items: center;
	}
	.link {
		align-self: flex-start;
		padding: 0;
		border: none;
		background: none;
		font: inherit;
		font-size: 13px;
		color: var(--accent);
		cursor: pointer;
	}
	.error {
		margin: 0;
		color: var(--down);
		font-size: 13px;
	}
	.found {
		font-size: 13px;
		padding: 10px;
		border-radius: 8px;
		background: var(--surface-2);
	}
</style>

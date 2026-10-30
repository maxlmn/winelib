<script lang="ts">
	import { emptyWine, newVintageDraft } from '#lib/api/forms.ts';
	import type { BottleDraft, Choice, Options, WineDraft, WineForm, WineSummary } from '#lib/api/forms.ts';
	import { request, messageOf } from '#lib/api/http.ts';
	import { links } from '#lib/links.ts';

	/** Fill from text: an order or auction email, an invoice or a producer's sheet pasted in fills the bottle form
	 * (POST /api/lookups/from-text): the wine (the one in WineLib, a new vintage of a cuvée it knows, or a new wine),
	 * the quantity, the price a bottle, the date and the vendor. A draft to check, nothing saved. */
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
	}

	let open = $state(false);
	let text = $state('');
	let busy = $state(false);
	let error = $state('');
	let found = $state<Found | null>(null);
	let how = $state('');

	async function fill() {
		if (!text.trim() || busy) return;
		busy = true;
		error = '';
		try {
			const f = await request<Found>('/api/lookups/from-text', { method: 'POST', body: { text } });
			if (f.wine_id) {
				wine = (await request<WineForm>(`/api/forms/wines/${f.wine_id}`)).summary;
				draft = null;
				how = 'already in WineLib';
			} else {
				let d: WineDraft;
				if (f.like_id) {
					d = newVintageDraft(await request<WineForm>(`/api/forms/wines/${f.like_id}`));
					how = 'a new vintage of a cuvée you have';
				} else {
					d = emptyWine(f.producer);
					how = f.producer?.id ? 'a new cuvée' : 'a new wine';
				}
				d.vintage = f.vintage || d.vintage;
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
		} catch (e) {
			found = null;
			error = messageOf(e);
		} finally {
			busy = false;
		}
	}
</script>

<div class="fill">
	{#if !open}
		<button type="button" class="link" onclick={() => (open = true)}>Fill from text: an order or auction email, an invoice…</button>
	{:else}
		<label for="b-text">Fill from text</label>
		<textarea id="b-text" rows="5" bind:value={text} placeholder="Paste the email or invoice: the wine, quantity, price, date and vendor are read from it"></textarea>
		<div class="row">
			<button type="button" class="btn" onclick={fill} disabled={busy || !text.trim()}>{busy ? 'Reading…' : 'Fill'}</button>
			<button type="button" class="link" onclick={() => ((open = false), (found = null), (error = ''))}>Close</button>
		</div>
		{#if error}<p class="error">{error}</p>{/if}
		{#if found}
			<div class="found">
				Read “{found.line}”: {how}{#if found.wine_id} (<a href={links.wine(found.wine_id)}>open it</a>){/if}.
				{[
					found.qty ? `${found.qty} × ` : '',
					found.price !== null ? `${found.price.toLocaleString()} ${found.currency ?? ''} a bottle` : '',
					found.price_total ? ` (${found.price_total.toLocaleString()} for the lot)` : '',
					found.purchase_date ? ` · ${found.purchase_date}` : '',
					found.vendor ? ` · ${found.vendor}` : ''
				].join('')}
				Check the fields below.
			</div>
		{/if}
	{/if}
</div>

<style>
	.fill {
		display: flex;
		flex-direction: column;
		gap: 6px;
		margin-bottom: 12px;
	}
	label {
		font-size: 13px;
		font-weight: 600;
	}
	textarea {
		width: 100%;
		font: inherit;
		font-size: 13px;
		resize: vertical;
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

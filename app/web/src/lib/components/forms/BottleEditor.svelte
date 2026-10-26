<script lang="ts">
	import { untrack } from 'svelte';
	import BottleFields from './BottleFields.svelte';
	import Field from './Field.svelte';
	import FormPage from './FormPage.svelte';
	import Section from './Section.svelte';
	import WinePicker from './WinePicker.svelte';
	import { blank, bottleDraft, check, num, remove, save, scoped, toBottleDetails, toWineIn, wineErrors } from '#lib/api/forms.ts';
	import type { BottleForm, Options, WineDraft, WineSummary } from '#lib/api/forms.ts';
	import { links } from '#lib/links.ts';
	import { plural } from '#lib/format.ts';

	let { options, bottle, wine: initialWine }: { options: Options; bottle: BottleForm | null; wine: WineSummary | null } = $props();

	// The form edits a copy; the route re-creates the editor for another bottle ({#key})
	const b = untrack(() => bottle);
	let wine = $state<WineSummary | null>(untrack(() => b?.wine ?? initialWine));
	let draft = $state<WineDraft | null>(null);
	let details = $state(bottleDraft(b));
	let qty = $state<number | null>(b ? b.qty : 1);
	let location = $state(blank(b?.location));
	let market = $state({
		last_price: b?.last_price || null, last_price_date: blank(b?.last_price_date), last_price_source: blank(b?.last_price_source)
	});
	let errors = $state<Record<string, string>>({});

	async function onsave() {
		check({
			...(!wine && !draft ? { wine: 'Pick the wine, or create a new one' } : {}),
			...(draft ? wineErrors(draft, 'wine.') : {}),
			...(qty === null || qty < 0 ? { qty: 'Quantity must be 0 or more' } : {})
		});
		const res = await save<{ id: number }>('bottles', b?.id ?? null, {
			wine: wine?.id ?? toWineIn(draft!),
			qty,
			location,
			...toBottleDetails(details),
			last_price: market.last_price,
			last_price_date: market.last_price_date || null,
			last_price_source: market.last_price_source
		});
		return links.bottle(res.id);
	}
</script>

<FormPage
	title={b ? 'Edit bottle' : 'Add bottle'}
	subtitle={b ? b.option.label : undefined}
	saveLabel="Save bottle"
	fallback={b ? links.bottle(b.id) : links.cellar()}
	{onsave}
	bind:fieldErrors={errors}
	remove={b
		? {
				what: 'this bottle',
				message: b.tastings ? `It has ${plural(b.tastings, 'tasting note')}: delete them first.` : 'This can’t be undone.',
				blocked: !!b.tastings,
				run: async () => links.wine((await remove<{ wine_id: number }>('bottles', b.id)).wine_id)
			}
		: undefined}
>
	<Section title="Wine">
		<WinePicker bind:wine bind:draft {options} prefix="b" errors={{ ...scoped(errors, 'wine'), wine: errors.wine }} />
	</Section>

	<Section title="Bottle">
		<div class="grid stack">
			<Field label="Quantity" for="b-qty" required error={errors.qty}>
				<input
					id="b-qty"
					type="number"
					min="0"
					step="1"
					value={qty ?? ''}
					aria-invalid={!!errors.qty}
					oninput={(e) => (qty = num(e.currentTarget.value))}
				/>
			</Field>
			<Field label="Location" for="b-location" hint="Bin or place, e.g. H3, Rack 2, Offsite">
				<input id="b-location" list="b-locations" bind:value={location} />
				<datalist id="b-locations">
					{#each options.locations as l}<option value={l}></option>{/each}
				</datalist>
			</Field>
		</div>
		<BottleFields bind:value={details} {options} prefix="b" {errors} />
	</Section>

	<Section title="Market price">
		<div class="grid three">
			<Field label="Last price" for="b-lp" hint="In the purchase currency" error={errors.last_price}>
				<input
					id="b-lp"
					type="number"
					min="0"
					step="0.01"
					value={market.last_price ?? ''}
					oninput={(e) => (market.last_price = num(e.currentTarget.value))}
				/>
			</Field>
			<Field label="Price date" for="b-lpd">
				<input id="b-lpd" type="date" bind:value={market.last_price_date} />
			</Field>
			<Field label="Price source" for="b-lps">
				<input id="b-lps" bind:value={market.last_price_source} placeholder="e.g. wine-searcher" />
			</Field>
		</div>
	</Section>
</FormPage>

<style>
	.stack {
		margin-bottom: 14px;
	}
</style>

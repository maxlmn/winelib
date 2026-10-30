<script lang="ts">
	import Field from './Field.svelte';
	import MoneyInput from './MoneyInput.svelte';
	import type { BottleDraft, Options } from '#lib/api/forms.ts';
	import { appSettings } from '#lib/settings.svelte.ts';

	/** Size, price, vendor, provenance and purchase date: shared by the bottle and tasting forms. */
	let { value = $bindable(), options, prefix, errors = {} }: { value: BottleDraft; options: Options; prefix: string; errors?: Record<string, string> } =
		$props();

	const sizes = $derived([...new Set([...options.bottle_sizes, value.bottle_size])]);

	// The vendor's buyer's premium (Settings), offered on the price typed: the hammer price to what it cost. Not
	// offered again on the price it made
	const premium = $derived.by(() => {
		const v = (value.vendor ?? '').trim().toLowerCase();
		const hit = v && Object.entries(appSettings.vendor_premiums ?? {}).find(([name]) => name.trim().toLowerCase() === v);
		return hit ? { vendor: hit[0], pct: hit[1] } : null;
	});
	let madeWith = $state<number | null>(null);
	const withPremium = $derived(premium && value.price ? Math.round(value.price * (100 + premium.pct)) / 100 : null);
</script>

<div class="grid three">
	<Field label="Bottle size" for="{prefix}-size">
		<select id="{prefix}-size" bind:value={value.bottle_size}>
			{#each sizes as s}<option value={s}>{s}</option>{/each}
		</select>
	</Field>
	<Field label="Purchase price" for="{prefix}-price" error={errors.price ?? errors.currency}>
		<MoneyInput
			id="{prefix}-price"
			price={value.price}
			currency={value.currency}
			currencies={options.currencies}
			invalid={!!(errors.price ?? errors.currency)}
			onchange={(p, c) => ((value.price = p), (value.currency = c))}
		/>
		{#if premium && withPremium && value.price !== madeWith}
			<!-- the total taken first: setting the price recomputes withPremium (on the new price) -->
			<button type="button" class="premium" onclick={() => { const total = withPremium; madeWith = total; value.price = total; }}
				title="The hammer price plus {premium.vendor}'s buyer's premium (Settings)">
				+ {premium.pct}% {premium.vendor} premium → {withPremium.toLocaleString()}
			</button>
		{/if}
	</Field>
	<Field label="Purchase date" for="{prefix}-date" error={errors.purchase_date}>
		<input id="{prefix}-date" type="date" bind:value={value.purchase_date} />
	</Field>
	<Field label="Vendor" for="{prefix}-vendor">
		<input id="{prefix}-vendor" bind:value={value.vendor} />
	</Field>
	<Field label="Provenance" for="{prefix}-prov" hint="Importer, seller, restaurant or who brought it">
		<input id="{prefix}-prov" bind:value={value.provenance} />
	</Field>
</div>

<style>
	.premium {
		margin-top: 4px;
		padding: 0;
		border: none;
		background: none;
		font: inherit;
		font-size: 12px;
		color: var(--accent);
		cursor: pointer;
		text-align: left;
	}
	.premium:hover {
		text-decoration: underline;
	}
</style>

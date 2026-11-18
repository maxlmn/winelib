<script lang="ts">
	import Field from './Field.svelte';
	import MoneyInput from './MoneyInput.svelte';
	import type { BottleDraft, Options } from '#lib/api/forms.ts';

	/** Size, price, vendor, provenance and purchase date: shared by the bottle and tasting forms. `dated: false`: no
	 * purchase date (a bottle bought for a tasting is bought that day) */
	let {
		value = $bindable(),
		options,
		prefix,
		errors = {},
		dated = true
	}: { value: BottleDraft; options: Options; prefix: string; errors?: Record<string, string>; dated?: boolean } = $props();

	const sizes = $derived([...new Set([...options.bottle_sizes, value.bottle_size])]);
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
	</Field>
	{#if dated}
		<Field label="Purchase date" for="{prefix}-date" error={errors.purchase_date}>
			<input id="{prefix}-date" type="date" bind:value={value.purchase_date} />
		</Field>
	{/if}
	<Field label="Vendor" for="{prefix}-vendor">
		<input id="{prefix}-vendor" bind:value={value.vendor} />
	</Field>
	<Field label="Provenance" for="{prefix}-prov" hint="Importer, seller, restaurant or who brought it">
		<input id="{prefix}-prov" bind:value={value.provenance} />
	</Field>
</div>


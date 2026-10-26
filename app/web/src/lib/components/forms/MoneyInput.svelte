<script lang="ts">
	import { appSettings } from '#lib/settings.svelte.ts';
	import { num } from '#lib/api/forms.ts';

	interface Props {
		id: string;
		price: number | null;
		currency: string;
		/** The currencies from /api/lookups/options */
		currencies: string[];
		invalid?: boolean;
		onchange: (price: number | null, currency: string) => void;
	}

	let { id, price, currency, currencies, invalid = false, onchange }: Props = $props();

	// Every currency with an exchange rate in Settings, and the bottle's own even if it has none
	const options = $derived([...new Set([...currencies, ...Object.keys(appSettings.exchange_rates), currency])]);
</script>

<div class="money">
	<input
		{id}
		type="number"
		inputmode="decimal"
		min="0"
		step="0.01"
		placeholder="0.00"
		value={price ?? ''}
		aria-invalid={invalid}
		oninput={(e) => onchange(num(e.currentTarget.value), currency)}
	/>
	<select aria-label="Currency" value={currency} onchange={(e) => onchange(price, e.currentTarget.value)}>
		{#each options as c}<option value={c}>{c}</option>{/each}
	</select>
</div>

<style>
	.money {
		display: flex;
	}
	.money input {
		border-top-right-radius: 0 !important;
		border-bottom-right-radius: 0 !important;
		min-width: 0;
	}
	.money select {
		width: auto !important;
		border-left: none !important;
		border-top-left-radius: 0 !important;
		border-bottom-left-radius: 0 !important;
	}
</style>
